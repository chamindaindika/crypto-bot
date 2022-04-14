#!/usr/bin/env python 

import sys, getopt, json, hmac, hashlib, time, requests, base64, os
from datetime import datetime
from dotenv import load_dotenv

try:
    # https://dev.to/jakewitcher/using-env-files-for-environment-variables-in-python-applications-55a1
    load_dotenv()

    # Before implementation, set environmental variables with the names API_KEY and API_SECRET
    BINANCE_API_KEY=os.getenv('BINANCE_API_KEY')
    BINANCE_API_SECRET=os.getenv('BINANCE_API_SECRET')

    coin_pair = ''
    from_asset = 'SHIB'
    to_asset = 'USDT'
    percentage_threshold = 1.2

    try:
        opts, args = getopt.getopt(sys.argv[1:], "ha:p:t:", ["assets_pair=", "base-price=", "threshold="])
    except getopt.GetoptError:
        print 'usage: app.py -a <assets_pair> -p <base_price> -t <percentage_threshold>'
        sys.exit(2)

    for opt, arg in opts:
        if '-h' == opt:
            print('usage: app.py -a <assets_pair> -p <base_price> -t <percentage_threshold>')
        elif opt in('-a', '--assets_pair'):
            coin_pair = arg.replace('/', '')
            list = arg.split('/')
            from_asset = list[0]
            to_asset = list[1]
        elif opt in('-p', '--base-price'):
            base_price = float(arg)
        elif opt in('-t', '--threshold'):
            percentage_threshold = arg

    sapi_url_v1 = 'https://api.binance.com/sapi/v1/'
    api_url_v3 = 'https://api.binance.com/api/v3/'

    bytes_secret = bytes(BINANCE_API_SECRET)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-MBX-APIKEY": BINANCE_API_KEY
    }

    while True:
        now = datetime.now()
        milliseconds = str(int(time.time()*1000.0))

        # Getting current spot price changes and calculate the percentage deference to determine the initial decision to go for a swap
        r = requests.get(api_url_v3 + 'ticker/price?symbol=' + coin_pair)
        main_asset_spot_price = float(r.json()['price'])
        stable_asset_spot_price = 1/float(r.json()['price'])

        # Getting current account balance for coin pair
        message = 'recvWindow=60000&timestamp=' + milliseconds
        bytes_message = bytes(message)
        signature = hmac.new(bytes_secret, bytes_message, hashlib.sha256).hexdigest()

        r = requests.get(api_url_v3 + 'account?recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
        res = r.json()['balances']
        print('Current Account Balances')
        print('-------------------------')
        for i in res:
            if float(i['free']) > 0:
                print(i)
                print(i['free'] + ' ' + i['asset'])

            if from_asset == i['asset']:
                main_asset_balance = float(i['free'])
            elif to_asset == i['asset']:
                stable_asset_balance = float(i['free'])

        # ================================================================================================================================
        
        # Getting fiat payment history
        message = 'transactionType=0&beginTime=1640995201000&recvWindow=60000&timestamp=' + milliseconds
        bytes_message = bytes(message)
        signature = hmac.new(bytes_secret, bytes_message, hashlib.sha256).hexdigest()

        r = requests.get(sapi_url_v1 + 'fiat/payments?transactionType=0&beginTime=1640995201000&recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
        res = r.json()['data']
        print('Coins Bought')
        print('-------------')
        for i in res:
            if 'Completed' == i['status']:
                print(i['cryptoCurrency'] + ': ' + i['obtainAmount'] + ' (' + i['sourceAmount'] + ' ' + i['fiatCurrency'] + ')')
        print('')


        # Getting current account balances
#        message = 'recvWindow=60000&timestamp=' + milliseconds
#        bytes_message = bytes(message)
#        signature = hmac.new(bytes_secret, bytes_message, hashlib.sha256).hexdigest()
#
#        r = requests.get(api_url_v3 + 'account?recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
#        res = r.json()['balances']
#        print('Current Account Balances')
#        print('-------------------------')
#        for i in res:
#            if float(i['free']) > 0:
#                print(i['free'] + ' ' + i['asset'])
#        print('')
#

        last_swap_time = 0
        last_convert_time = 0
        last_swap_base_price = 0
        last_convert_base_price = 0
        last_swap_quantity = 0
        last_convert_quantity = 0

        # Getting SWAP History
        message = 'recvWindow=60000&timestamp=' + milliseconds
        bytes_message = bytes(message)
        signature = hmac.new(bytes_secret, bytes_message, hashlib.sha256).hexdigest()
        r = requests.get(sapi_url_v1 + 'bswap/swap?recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
        res = r.json()
#        print('SWAP History')
#        print('-------------')
        for i in res:
            if True == i['status']:
#                print(i['quoteQty'] + ' ' + i['quoteAsset'] + ' => ' + i['baseQty'] + ' ' + i['baseAsset'])
                if (from_asset == i['quoteAsset'] and to_asset == i['baseAsset']) or (to_asset == i['quoteAsset'] and from_asset == i['baseAsset']):
                    last_swap_time = i['swapTime']
                    last_swap_base_price = 1/float(i['price'])
                    last_swap_quantity = i['baseQty']
#        print('')

        # Getting Convert History
        message = 'startTime=1640995201000&endTime=' + milliseconds + '&recvWindow=60000&timestamp=' + milliseconds
        bytes_message = bytes(message)
        signature = hmac.new(bytes_secret, bytes_message, hashlib.sha256).hexdigest()
        r = requests.get(sapi_url_v1 + 'convert/tradeFlow?startTime=1640995201000&endTime=' + milliseconds + '&recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
        res = r.json()['list']
#        print('Convert History')
#        print('----------------')
        for i in res:
            if 'SUCCESS' == i['orderStatus']:
#                print(i['fromAmount'] + ' ' + i['fromAsset'] + ' => ' + i['toAmount'] + ' ' + i['toAsset'])
#                print(i)
                if (from_asset == i['fromAsset'] and to_asset == i['toAsset']) or (to_asset == i['fromAsset'] and from_asset == i['toAsset']):
#                    print(i)
                    last_convert_time = i['createTime']
#                    last_convert_base_price = i['ratio']
#                    last_convert_quantity = i['toAmount']
                    
                    if from_asset == i['fromAsset']:
                        last_convert_base_price = i['ratio']
                        last_convert_quantity = i['fromAmount']
                        current_spot_price = main_asset_spot_price
                    elif from_asset == i['toAsset']:
                        last_convert_base_price = i['inverseRatio']
                        last_convert_quantity = i['toAmount']
                        current_spot_price = main_asset_spot_price
        print('')

        if last_swap_time > last_convert_time:
            base_price = float(last_swap_base_price)
            swap_quantity = last_swap_quantity
        else:
            base_price = float(last_convert_base_price)
            swap_quantity = last_convert_quantity
        
        # ================================================================================================================================

        print('Main Asset - ' + from_asset)
        print('Stable Asset - ' + to_asset)
        print('Main Asset Balance - ' + str(main_asset_balance))
        print('Stable Asset Balance - ' + str(stable_asset_balance))
        print('Base Price - ' + str(base_price))
        print('Currernt Spot Pirce - ' + str(current_spot_price))

        percentage = (current_spot_price - base_price) / base_price * 100
        percentage = round(percentage, 3)

        print('Percentage Difference - ' + str(percentage) + '%')
        print('Swap Quantity - ' + str(swap_quantity))
        print('')
#        exit()

        # (-) toAsset (USDT) -> fromAsset (AXS)
        if percentage <= -float(percentage_threshold):
            print(now.strftime("%d/%m/%Y %H:%M:%S") + ' (' + str(base_price) + ' => ' + str(current_spot_price) + ' | ' + str(percentage) + '%) - Swapping ' + to_asset + ' => ' + from_asset)

            # Need to get minimum amount by the API
            if stable_asset_balance > 10 and stable_asset_balance > swap_quantity:
                # Getting SWAP History For USDT -> AXS
#                message = 'quoteAsset=' + from_asset + '&baseAsset=' + to_asset + '&recvWindow=60000&timestamp=' + milliseconds
#                bytes_message = bytes(message)
#                signature = hmac.new(bytes_secret, bytes_message, hashlib.sha256).hexdigest()
#                r = requests.get(sapi_url_v1 + 'bswap/swap?quoteAsset=' + from_asset + '&baseAsset=' + to_asset + '&recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
#                if True == bool(r.json()):
#                    res = r.json()
#                    swap_quantity = res['baseQty']
#                else:
#                    swap_quantity = current_to_asset_balance

#                if last_swap_time > last_convert_time:
#                    swap_quantity = last_swap_quantity
#                else:
#                    swap_quantity = last_convert_quantity

                # Getting SWAP Quote to make the decision whether we really go for a swap
                message = 'quoteAsset=' + to_asset + '&baseAsset=' + from_asset + '&quoteQty=' + str(swap_quantity) + '&recvWindow=60000&timestamp=' + milliseconds
                bytes_message = bytes(message)
                signature = hmac.new(bytes_secret, bytes_message, hashlib.sha256).hexdigest()
                r = requests.get(sapi_url_v1 + 'bswap/quote?quoteAsset=' + to_asset + '&baseAsset=' + from_asset + '&quoteQty=' + str(swap_quantity) + '&recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
                res = r.json()
                coin_swap_price = float(res['price'])
                USDT_swap_price = 1/float(res['price'])
                swapped_quantity = res['baseQty']

                # Perform actual swap process
    #            r = requests.post(sapi_url_v1 + 'bswap/swap?quoteAsset=' + to_asset + '&baseAsset=' + from_asset + '&quoteQty=' + str(swap_quantity) + '&recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
    #            swap_id = r.json()['swapId']

                print(to_asset + ': ' + str(swap_quantity) + ' => ' + from_asset + ': ' + str(swapped_quantity) + ' [SPOT: 1 USDT = ' + str(current_spot_price) + ' ' + from_asset + ' | SWAP: 1 USDT = ' + str(USDT_swap_price) + ' ' + from_asset + ']')
    #            print('Swapp Successful >>>>>>>> SAWP Entity ID: ' + swap_id)
            else:
                print('Not enough account balance - ' + str(stable_asset_balance) + ' ' + to_asset)

            print('')

        # (+) fromAsset (AXS) -> toAsset (USDT)
        elif percentage >= float(percentage_threshold):
            print(now.strftime("%d/%m/%Y %H:%M:%S") + ' (' + str(base_price) + ' => ' + str(current_spot_price) + ' | ' + str(percentage) + '%) - Swapping ' + from_asset + ' => ' + to_asset)

            # Need to get minimum amount by the API
            if main_asset_balance > 0.02 and main_asset_balance > swap_quantity:
                # Getting SWAP History For AXS -> USDT
#                message = 'quoteAsset=' + from_asset + '&baseAsset=' + to_asset + '&recvWindow=60000&timestamp=' + milliseconds
#                bytes_message = bytes(message)
#                signature = hmac.new(bytes_secret, bytes_message, hashlib.sha256).hexdigest()
#                r = requests.get(sapi_url_v1 + 'bswap/swap?quoteAsset=' + from_asset + '&baseAsset=' + to_asset + '&recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
#                print(r.json())
#                if True == bool(r.json()):
#                    res = r.json()
#                    swap_quantity = res['baseQty']
#                else:
#                    swap_quantity = current_from_asset_balance

#                if last_swap_time > last_convert_time:
#                    swap_quantity = last_swap_quantity
#                else:
#                    swap_quantity = last_convert_quantity

                # Getting SWAP Quote to make the decision whether we really go for a swap
                message = 'quoteAsset=' + from_asset + '&baseAsset=' + to_asset + '&quoteQty=' + str(swap_quantity) + '&recvWindow=60000&timestamp=' + milliseconds
                bytes_message = bytes(message)
                signature = hmac.new(bytes_secret, bytes_message, hashlib.sha256).hexdigest()
                r = requests.get(sapi_url_v1 + 'bswap/quote?quoteAsset=' + from_asset + '&baseAsset=' + to_asset + '&quoteQty=' + str(swap_quantity) + '&recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
                res = r.json()
                USDT_swap_price = float(res['price'])
                coin_swap_price = 1/float(res['price'])
                swapped_quantity = res['baseQty']
                
                # Perform actual swap process
    #            r = requests.post(sapi_url_v1 + 'bswap/swap?quoteAsset=' + from_asset + '&baseAsset=' + to_asset + '&quoteQty=' + str(swap_quantity) + '&recvWindow=60000&timestamp=' + milliseconds + '&signature=' + signature, headers=headers)
    #            swap_id = r.json()['swapId']

                print(from_asset + ': ' + str(swap_quantity) + ' => ' + to_asset + ': ' + str(swapped_quantity) + ' [SPOT: 1 ' + from_asset + ' = ' + str(current_spot_price) + ' ' + to_asset + ' | SWAP: 1 ' + from_asset + ' = ' + str(coin_swap_price) + ' ' + to_asset + ']')
    #            print('Swapp Successful >>>>>>>> SAWP Entity ID: ' + swap_id)
            else:
                print('Not enough account balance - ' + str(main_asset_balance) + ' ' + from_asset)

            print('')
        else:
            print('Percentage of difference: ' + str(percentage) + '% [ Current Price: ' + str(current_spot_price) + ' | Base Price: ' + str(base_price) + '] >>>>>>>> Skipping....')

        time.sleep(5)

except KeyboardInterrupt:
    sys.exit(0)
