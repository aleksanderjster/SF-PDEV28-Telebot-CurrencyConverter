import telebot
import requests
from requests.structures import CaseInsensitiveDict
import json

from auth_data import bot_token
from auth_data import currency_converter_api_url as api_url
from auth_data import currency_converter_api_key as api_key
from config_data import currency_dict


class ConversionException(Exception):
    pass


class CurrencyConverter:
    def __init__(self):
        self.currency_rates = {}
        self.get_currency_rates()

    def get_currency_rates(self):
        headers = CaseInsensitiveDict()
        headers["apikey"] = api_key
        try:
            resp = requests.get(api_url, headers=headers)
            self.currency_rates = json.loads(resp.content)['data']
        except ConnectionError:
            raise Exception('Unable get currency rates from server')

    def get_currency_rate(self, currency_ticker: str):
        rate = self.currency_rates[currency_ticker]
        return '{:.2f}'.format(rate)

    def get_currency_ticker(self, currency_name: str):
        if len(currency_name) == 3:                         # check if given name is ticker
            currency_name = currency_name.upper()
            currency_codes = self.currency_rates.keys()
            if currency_name not in currency_codes:
                raise ConversionException(f'Currency - {currency_name} is not in the currency list. /help')
            else:
                return currency_name
        else:                                               # attempt to get ticker by alternative name
            currency_name = currency_name.lower()
            if currency_name not in currency_dict.keys():
                raise ConversionException(f'Alternative currency name - {currency_name} is not correct. /help')
            else:
                return currency_dict[currency_name]

    def get_amount_to_sell(self, curr_to_buy: str, curr_to_sell: str, amount_to_buy: float):
        rate_to_buy = float(self.get_currency_rate(curr_to_buy))
        rate_to_sell = float(self.get_currency_rate(curr_to_sell))

        return '{:.2f}'.format((rate_to_sell / rate_to_buy) * amount_to_buy)


class Converter:
    @staticmethod
    def get_amount_to_sell(currency_converter: CurrencyConverter,
                           curr_buy: str,
                           curr_sell: str,
                           amount_to_buy: str):

        if str(curr_buy).lower() == str(curr_sell).lower():
            raise ConversionException(f'Sell and Buy currencies can not be the same!')

        try:
            amount_to_buy = float(amount_to_buy)
        except ValueError:
            raise ConversionException(f'Amount = {amount_to_buy} is not valid number!')

        try:
            curr_buy = currency_converter.get_currency_ticker(curr_buy)
        except KeyError as e:
            raise ConversionException(e)

        try:
            curr_sell = currency_converter.get_currency_ticker(curr_sell)
        except KeyError as e:
            raise ConversionException(e)
        try:
            amount_to_sell = currency_converter.get_amount_to_sell(curr_buy, curr_sell, amount_to_buy)
        except ConversionException as e:
            raise ConversionException(e)
        else:
            return amount_to_sell


def telegram_bot():
    bot = telebot.TeleBot(bot_token)
    currency_converter = CurrencyConverter()

    @bot.message_handler(commands=['start', 'help'])
    def start_message(message: telebot.types.Message):
        usr = message.chat.username
        currency_codes = currency_converter.currency_rates.keys()
        bot.reply_to(message, f'Hello {usr}!\n'
                              f'You can get price for amount of currency you want to buy\n'
                              f'Make your input in follow sequence:\n\n'
                              f'Currency(to buy) Currency(to sell) Amount(currency to buy)\n\n'
                              f'Follow common names can be used as currency names:\n'
                              f'USD / dollar / доллар\n'
                              f'EUR / euro / евро\n'
                              f'RUB / ruble / рубль\n'
                              f'or other currency codes can be used from follow list:\n'
                              f'{", ".join(list(currency_codes))}\n')

    @bot.message_handler(content_types=['text'])
    def treat_message(message: telebot.types.Message):
        try:
            try:
                curr_buy, curr_sell, amount_to_buy = message.text.split(' ')
            except ValueError:
                raise ConversionException('Wrong amount of input parameters. 3 parameters needed.\n')

            amount_to_sell = Converter.get_amount_to_sell(currency_converter, curr_buy, curr_sell, amount_to_buy)
            curr_buy = currency_converter.get_currency_ticker(curr_buy)
            curr_sell = currency_converter.get_currency_ticker(curr_sell)
            bot.reply_to(message, f'{amount_to_buy} {curr_buy} = {amount_to_sell} {curr_sell}')
        except ConversionException as e:
            bot.reply_to(message, f'User input error: \n{e}')
        except Exception as e:
            bot.reply_to(message, f'Execution error: \n{e}')

    bot.polling(none_stop=True)
