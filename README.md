# Turtle-Strategy 
This strategy is applied on Future Dow30EMini on hourly basis. Signals are generated when the price break previous high or low. A trailing stop loss strategy is done by simply applying Average True Range

# Objective
The objective of writing this strategy is to test if the turtle strategy still works since its invention by the legendary commodity traders Richard Dennis.  

# Signals Generation
A buy signal is generated when the price breaks previous high within 20 days with a bullish candlestick. Similarly, a sell signal is generated if price breaks previous low within 20 days with a bearish candlestick.

# Trailing stop loss
The stop loss strategy is by applying Average True Range (ATR). The stop loss is calculated by subtracting close price by 1 ATR. When in a long position, the trailing stop loss will by pushed up if the current close price is higher than previous close. When in a short position, the trailing stop loss will by recalculated if the current close price is lower than previous close. 

Backtest result is attached as below for the year of 2018:

![alt text](https://github.com/kelvonlys/Turtle-Strategy/blob/main/Turtle.png)





