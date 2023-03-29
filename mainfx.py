import fxcmpy
import pandas as pd
import talib

# Define FXCM API credentials
fxcm_access_token = 'YOUR_FXCM_ACCESS_TOKEN'
fxcm_account_id = 'YOUR_FXCM_ACCOUNT_ID'

# Connect to FXCM API
api = fxcmpy.fxcmpy(access_token=fxcm_access_token, log_level='error')

# Define trading parameters
pair = 'EUR/USD'
units = 10000
sl_distance = 0.02
tp_distance = 0.03
stop_loss = 0
take_profit = 0
trade_count = 0

# Define functions for each strategy
def trend_following_strategy(data):
    # Use Moving Averages to determine trend direction
    ma_fast = talib.MA(data['close'], timeperiod=50, matype=0)
    ma_slow = talib.MA(data['close'], timeperiod=200, matype=0)

    # Check for trend direction
    if ma_fast[-1] > ma_slow[-1]:
        return 'buy'
    elif ma_fast[-1] < ma_slow[-1]:
        return 'sell'
    else:
        return 'hold'

def mean_reversion_strategy(data):
    # Use Bollinger Bands to determine mean and standard deviation
    upper, middle, lower = talib.BBANDS(data['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)

    # Check for oversold or overbought conditions
    if data['close'][-1] < lower[-1]:
        return 'buy'
    elif data['close'][-1] > upper[-1]:
        return 'sell'
    else:
        return 'hold'

def breakout_strategy(data):
    # Use Average True Range to determine volatility
    atr = talib.ATR(data['high'], data['low'], data['close'], timeperiod=14)

    # Check for breakout conditions
    if data['close'][-1] > data['high'][-2] + atr[-2]:
        return 'buy'
    elif data['close'][-1] < data['low'][-2] - atr[-2]:
        return 'sell'
    else:
        return 'hold'


# Define risk management function
def apply_risk_management(position, current_price):
    global stop_loss, take_profit

    # Calculate stop loss and take profit levels based on current price
    if position == 'buy':
        stop_loss = current_price - (current_price * sl_distance)
        take_profit = current_price + (current_price * tp_distance)
    elif position == 'sell':
        stop_loss = current_price + (current_price * sl_distance)
        take_profit = current_price - (current_price * tp_distance)

    # Update stop loss and take profit levels for the trade
    api.change_trade_stop_limit(trade_id=trade_count, is_in_pips=False, is_stop=True, rate=stop_loss)
    api.change_trade_stop_limit(trade_id=trade_count, is_in_pips=False, is_stop=False, rate=take_profit)

# Main trading loop
while True:
    # Get current market data
    data = api.get_candles(pair, period='m5', number=401)

    # Reformat data
    data = pd.DataFrame(data)
    data['time'] = pd.to_datetime(data['time'], unit='ms')
    data = data.set_index('time')
    data = data[['askclose', 'askopen', 'bidclose', 'bidopen']]
    data.columns = ['close', 'open', 'close_ask', 'open_ask']

    # Execute trading strategies
    tf_signal = trend_following_strategy(data)
    mr_signal = mean_reversion_strategy(data)
    bo_signal = breakout_strategy(data)

    # Determine overall signal based on combination of individual signals
    signal = ''
    if tf_signal == 'buy' and mr_signal == 'buy' and bo_signal == 'buy':
        signal = 'buy'
    elif tf_signal == 'sell' and mr_signal == 'sell' and bo_signal == 'sell':
        signal = 'sell'
    else:
        signal = 'hold'

    # Execute trade based on signal
    if signal == 'buy' and trade_count == 0:
        # Open buy position
        response = api.create_market_buy_order(pair, units, stop_loss=stop_loss, take_profit=take_profit)
        trade_count += 1

        # Apply risk management
        apply_risk_management('buy', response['open'])

    elif signal == 'sell' and trade_count == 0:
        # Open sell position
        response = api.create_market_sell_order(pair, units, stop_loss=stop_loss, take_profit=take_profit)
        trade_count += 1

        # Apply risk management
        apply_risk_management('sell', response['open'])
    
    elif trade_count == 1:
        # Check the status of the open trade
        trade_status = api.get_open_trade_ids()[0]['tradeStatus']

        if trade_status == 'Open':
            # Update stop loss and take profit levels based on current price
            current_price = api.get_last_price(pair)
            apply_risk_management(signal, current_price)
            
        elif trade_status == 'Closed':
            # Reset variables
            stop_loss = 0
            take_profit = 0


       
