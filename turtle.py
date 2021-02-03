import clr
import decimal as d

import pandas as pd

class FuturesBollKD(QCAlgorithm):

    def Initialize(self):
        self.contract = None
        self.SetStartDate(2018, 1, 1)    #Set Start Date
        self.SetEndDate(2018, 12, 31)      #Set End Date   
        
        # self.SetStartDate(2019, 12, 1) 
        self.cash = 4000
        self.SetCash(self.cash)             #Set Strategy Cash
        self.riskPercentage = 0.02
        self.leverage = 1
        
        self.new_day = True
        self.reset = True
        
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        self.Settings.FreePortfolioValuePercentage = 0.3
        
        # Subscribe and set our expiry filter for the futures chain
        # futureES = self.AddFuture(Futures.Indices.SP500EMini)#Futures.Indices.Dow30EMini 
        futureES = self.AddFuture(Futures.Indices.Dow30EMini)
        futureES.SetFilter(TimeSpan.Zero, TimeSpan.FromDays(360))           
        
        self.maxAmountOfRisk = self.cash * self.riskPercentage
        
        self.maxIndicator = Maximum(20)
        self.minIndicator = Minimum(20)  
        self.trailingStopIndicator = AverageTrueRange(10)
        self.linearRegression = LeastSquaresMovingAverage(120)
        
        self.previousClose = RollingWindow[float](2)
        self.periodMaxValue = RollingWindow[float](2)
        self.periodMinValue = RollingWindow[float](2)
        
        self.stopCallLoss = 0
        self.stopPutLoss = 0
        
        # self.InitializeGraph()
        self.SetWarmUp(3)
        
        ### for stop loss and take profit
        
        
    def OnData(self, slice):
        
        if not self.InitUpdateContract(slice):
            return
        
        # Reset any open positions based on a contract rollover.
        if self.reset:
            self.reset = False
            self.Log('RESET: closing all positions')
            self.Liquidate()
            
    def InitUpdateContract(self, slice):
        # Reset daily - everyday we check whether futures need to be rolled
        if not self.new_day:
            return True
            
        if self.contract != None and (self.contract.Expiry - self.Time).days >= 3: # rolling 3 days before expiry
            return True             
                        
        for chain in slice.FutureChains.Values:
            # When selecting contract, if on expiry date then skip first as it would be the same one.
            idx = 0
            if self.contract != None:
                self.Log('Expiry days away {} - {}'.format((self.contract.Expiry-self.Time).days, self.contract.Expiry))
            if self.contract != None and (self.contract.Expiry - self.Time).days < 3:
                idx = 1
            
            contracts = list(chain.Contracts.Values)
            
            chain_contracts = list(contracts) #[contract for contract in chain]
            chain_contracts = sorted(chain_contracts, key=lambda x: x.Expiry)
            
            if len(chain_contracts) < 2:
                return False
                
            first = chain_contracts[idx]
            second = chain_contracts[idx+1]
            
            if (first.Expiry - self.Time).days >= 3:
                self.contract = first
            elif (first.Expiry - self.Time).days < 3 and (second.Expiry - self.Time).days >= 3:
                self.contract = second
            self.Log("Setting contract to: {}".format(self.contract.Symbol.Value))
            
            self.new_day = False
            self.reset = True
                            
            #Set up 60 minutes consolidator
            self.consolidator = TradeBarConsolidator(timedelta(minutes=60))
            self.consolidator.DataConsolidated += self.MinuteHandler
            self.SubscriptionManager.AddConsolidator(self.contract.Symbol, self.consolidator)
            
            # Set up 1 minute consolidator
            oneMinConsolidator = TradeBarConsolidator(timedelta(minutes=1))
            oneMinConsolidator.DataConsolidated += self.OneMinuteHandler
            self.SubscriptionManager.AddConsolidator(self.contract.Symbol, oneMinConsolidator)
            
            # self.RegisterIndicator(self.contract.Symbol, self.volumeMA, self.consolidator)
            self.RegisterIndicator(self.contract.Symbol, self.maxIndicator, self.consolidator)
            self.RegisterIndicator(self.contract.Symbol, self.minIndicator, self.consolidator)
            self.RegisterIndicator(self.contract.Symbol, self.trailingStopIndicator, self.consolidator)
            self.RegisterIndicator(self.contract.Symbol, self.linearRegression, self.consolidator)
            
            self.SetWarmUp(TimeSpan.FromDays(2)) # Set warm up
            
            return True
        return False
    
    def OneMinuteHandler(self, sender, data):
        if self.IndicatorsAreReady and self.WindowsAreReady:
            if self.Portfolio[self.contract.Symbol].IsLong :
                if self.FlatCall(data.Close):  
                    self.Liquidate()
                                    
            if self.Portfolio[self.contract.Symbol].IsShort:
                if self.FlatPut(data.Close): 
                    self.Liquidate()                    
    
    def MinuteHandler(self, sender, consolidated):
        self.consolidated = consolidated
        self.SetUpRollingWindow()
        slope = self.linearRegression.Slope.Current.Value
        
        if self.Portfolio[self.contract.Symbol].IsLong:
            self.CalCallStopLoss()
            
        if self.Portfolio[self.contract.Symbol].IsShort:
            self.CalPutStopLoss()
        
        # if (self.Time.hour < 10) or self.Time.hour > 16:
        #     return
        
        if self.IndicatorsAreReady and self.WindowsAreReady:
            if (not self.Portfolio.Invested) and self.GetLongSignal >= 0.5 and slope > -0.5:
                if self.GetLongSignal == 0.9:
                    self.SetHoldings(self.contract.Symbol, 0.9)
                elif self.GetLongSignal == 0.7:
                    self.SetHoldings(self.contract.Symbol, 0.7)
                # elif self.GetLongSignal == 0.5:
                #     self.SetHoldings(self.contract.Symbol, 0.5)
                self.stopCallLoss = self.consolidated.Close - self.trailingStopIndicator.Current.Value
            
            if (not self.Portfolio.Invested) and self.GetShortSignal >= 0.5 and slope <= -1:
                
                self.SetHoldings(self.contract.Symbol, -0.5)
                    
                self.stopPutLoss = self.consolidated.Close + self.trailingStopIndicator.Current.Value
            
            self.PlotGraph(consolidated)
    def SetUpRollingWindow(self):
        self.previousClose.Add(self.consolidated.Close)
        self.periodMaxValue.Add(self.maxIndicator.Current.Value)
        self.periodMinValue.Add(self.minIndicator.Current.Value)
    
    @property 
    def GetLongSignal(self): 
        close = self.consolidated.Close
        open = self.consolidated.Open                  
        
        bullishCandle = 0
        breakout = 0
        breakPreviousHigh = 0
            
        if close - open != 0:
            bullishCandle = self.BullishCandle(open,close)
            breakPreviousHigh = close - self.periodMaxValue[1]
            breakout = breakPreviousHigh / abs(close - open)
        
        if breakout >= 0.5 and bullishCandle >= 0.5:
            return 0.9
        elif breakPreviousHigh > 0 and bullishCandle >= 0.5:
            return 0.7
        # elif breakPreviousHigh > 0:
        #     return 0.5
        else:
            return 0
        # self.Debug(f"date: {self.Time} perdioMaxValue: {self.periodMaxValue} close: {close} ")
        # if close > self.periodMaxValue[1]:
        #     return True
     
    @property
    def GetShortSignal(self):
        close = self.consolidated.Close
        open = self.consolidated.Open                  
        
        bearishCandle = 0
        breakout = 0
        breakPreviousLow = 0
            
        if close - open != 0:
            bearishCandle = self.BearishCandle(open, close)
            breakPreviousLow = close - self.periodMinValue[1]
            breakout = breakPreviousLow / abs(open - close)
            
        if breakPreviousLow < 0:
            return 0.5
        else:
            return 0
    
    def FlatCall(self, close):
        if close < self.stopCallLoss:
            self.stopCallLoss = 0
            return True
    
    def FlatPut(self, close):
        if close > self.stopPutLoss:
            self.stopPutLoss = 0
            return True
    
    def BullishCandle(self, open, close):
        High = self.consolidated.High
        Low = self.consolidated.Low
        
        return (close - open)/abs(High-Low)
        
    def BearishCandle(self, open, close):
        High = self.consolidated.High
        Low = self.consolidated.Low
        
        return (open - close)/abs(High-Low)
    
    def CalCallStopLoss(self):
        if self.consolidated.Close >= self.previousClose[1]:
            self.stopCallLoss = self.consolidated.Close - self.trailingStopIndicator.Current.Value
    
    def CalPutStopLoss(self):
        if self.consolidated.Close <= self.previousClose[1]:
            self.stopPutLoss = self.consolidated.Close + self.trailingStopIndicator.Current.Value
    
    @property
    def IndicatorsAreReady(self):
        if self.maxIndicator.IsReady and self.minIndicator.IsReady and self.trailingStopIndicator.IsReady:
            return True
        else:
            return False
            
    @property
    def WindowsAreReady(self):
        if self.previousClose.IsReady:
            return True
        else:
            return False
    
    def PlotGraph(self, consolidated):
        self.Plot("Band", "Close Price", consolidated.Close)
        self.Plot("Band", "Open", consolidated.Open)
        self.Plot("Band", "High", consolidated.High)
        self.Plot("Band", "Low", consolidated.Low)
        self.Plot("Band", "Previous Max", self.periodMaxValue[1])
        self.Plot("Stop loss graph", "Stop loss", self.stopCallLoss)
        self.Plot("Stop loss graph", "Stop Short loss", self.stopPutLoss)
        self.Plot("Band", "Previous Min", self.periodMinValue[1])
    
    def DailyHandler(self, consolidated):
        pass
    
    def OnEndOfDay(self):
        self.new_day = True
