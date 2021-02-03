# Turtle-Strategy with ATR as trailing stop loss
This strategy is inspired by the famous turtle strategy. Signals are generated when the price break previous high or low. A trailing stop loss strategy is done by simply applying Average True Range

![alt text](https://github.com/kelvonlys/Stock-Price-Visualisation/blob/main/graph.png)

# Trailing stop loss
The stop loss strategy is by applying Average True Range (ATR). The stop loss is calculated by subtracting close price by 1 ATR. When in a long position, the trailing stop loss will by pushed up if the current close price is higher than previous close. When in a short position, the trailing stop loss will by recalculated if the current close price is lower than previous close. 



