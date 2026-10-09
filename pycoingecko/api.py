import json
import os
import requests
import time

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .utils import func_args_preprocessing


class CoinGeckoAPI:
    __API_URL_BASE = 'https://api.coingecko.com/api/v3/'

    def __init__(self, api_base_url=__API_URL_BASE, api_key: str = ''):
        self.api_base_url = api_base_url
        self.api_key = api_key or os.getenv('COINGECKO_PRO_API_KEY', '')
        self.request_timeout = 120
        self.onchain_page_retries = 2
        self.onchain_page_retry_delay = 15.0

        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({'x-cg-pro-api-key': self.api_key})
        # CoinGecko occasionally returns HTTP 408 while building large on-chain
        # pool pages. GET requests are safe to retry, including rate limits and
        # transient upstream failures. Retry-After is honored when supplied.
        retries = Retry(
            total=5,
            connect=5,
            read=5,
            status=5,
            backoff_factor=0.5,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=frozenset(['GET']),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def __request(self, url):
        # print(url)
        try:
            response = self.session.get(url, timeout=self.request_timeout)
        except requests.exceptions.RequestException:
            raise

        try:
            response.raise_for_status()
            content = json.loads(response.content.decode('utf-8'))
            return content
        except Exception as e:
            # check if json (with error message) is returned
            try:
                content = json.loads(response.content.decode('utf-8'))
                raise ValueError(content)
            # if no json
            except json.decoder.JSONDecodeError:
                pass

            raise

    def __request_onchain_page(self, url):
        """Retry expensive on-chain pages slowly after HTTP retries are exhausted."""
        for attempt in range(self.onchain_page_retries + 1):
            try:
                return self.__request(url)
            except requests.exceptions.RequestException:
                if attempt >= self.onchain_page_retries:
                    raise
                time.sleep(self.onchain_page_retry_delay * (2 ** attempt))

    def __api_url_params(self, api_url, params, api_url_has_params=False):
        if params:
            # if api_url contains already params and there is already a '?' avoid
            # adding second '?' (api_url += '&' if '?' in api_url else '?'); causes
            # issues with request parametes (usually for endpoints with required
            # arguments passed as parameters)
            api_url += '&' if api_url_has_params else '?'
            for key, value in params.items():
                if type(value) == bool:
                    value = str(value).lower()

                api_url += "{0}={1}&".format(key, value)
            api_url = api_url[:-1]
        return api_url

    # ---------- PING ----------#
    def ping(self):
        """Check API server status"""

        api_url = '{0}ping'.format(self.api_base_url)
        return self.__request(api_url)

    # ---------- SIMPLE ----------#
    @func_args_preprocessing
    def get_price(self, ids, vs_currencies, **kwargs):
        """Get the current price of any cryptocurrencies in any other supported currencies that you need"""

        ids = ids.replace(' ', '')
        kwargs['ids'] = ids
        vs_currencies = vs_currencies.replace(' ', '')
        kwargs['vs_currencies'] = vs_currencies

        api_url = '{0}simple/price'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_token_price(self, id, contract_addresses, vs_currencies, **kwargs):
        """Get the current price of any tokens on this coin (ETH only at this stage as per api docs) in any other supported currencies that you need"""

        contract_addresses = contract_addresses.replace(' ', '')
        kwargs['contract_addresses'] = contract_addresses
        vs_currencies = vs_currencies.replace(' ', '')
        kwargs['vs_currencies'] = vs_currencies

        api_url = '{0}simple/token_price/{1}'.format(self.api_base_url, id)
        api_url = self.__api_url_params(api_url, kwargs)
        return self.__request(api_url)

    @func_args_preprocessing
    def get_supported_vs_currencies(self, **kwargs):
        """Get list of supported_vs_currencies"""

        api_url = '{0}simple/supported_vs_currencies'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- COINS ----------#
    @func_args_preprocessing
    def get_coins(self, **kwargs):
        """List all coins with data (name, price, market, developer, community, etc)"""

        api_url = '{0}coins'.format(self.api_base_url)
        # ['order', 'per_page', 'page', 'localization']
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coins_list(self, **kwargs):
        """List all supported coins id, name and symbol (no pagination required)"""

        api_url = '{0}coins/list'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coins_markets(self, vs_currency, **kwargs):
        """List all supported coins price, market cap, volume, and market related data"""

        kwargs['vs_currency'] = vs_currency

        api_url = '{0}coins/markets'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coin_by_id(self, id, **kwargs):
        """Get current data (name, price, market, ... including exchange tickers) for a coin"""

        api_url = '{0}coins/{1}/'.format(self.api_base_url, id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coin_ticker_by_id(self, id, **kwargs):
        """Get coin tickers (paginated to 100 items)"""

        api_url = '{0}coins/{1}/tickers'.format(self.api_base_url, id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coin_history_by_id(self, id, date, **kwargs):
        """Get historical data (name, price, market, stats) at a given date for a coin"""

        kwargs['date'] = date

        api_url = '{0}coins/{1}/history'.format(self.api_base_url, id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coin_market_chart_by_id(self, id, vs_currency, days, **kwargs):
        """Get historical market data include price, market cap, and 24h volume (granularity auto)"""

        api_url = '{0}coins/{1}/market_chart?vs_currency={2}&days={3}'.format(self.api_base_url, id, vs_currency, days)
        api_url = self.__api_url_params(api_url, kwargs, api_url_has_params=True)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coin_market_chart_range_by_id(self, id, vs_currency, from_timestamp, to_timestamp, **kwargs):
        """Get historical market data include price, market cap, and 24h volume within a range of timestamp (granularity auto)"""

        api_url = '{0}coins/{1}/market_chart/range?vs_currency={2}&from={3}&to={4}'.format(self.api_base_url, id,
                                                                                           vs_currency, from_timestamp,
                                                                                           to_timestamp)
        api_url = self.__api_url_params(api_url, kwargs, api_url_has_params=True)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coin_status_updates_by_id(self, id, **kwargs):
        """Get status updates for a given coin"""

        api_url = '{0}coins/{1}/status_updates'.format(self.api_base_url, id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coin_ohlc_by_id(self, id, vs_currency, days, **kwargs):
        """Get coin's OHLC"""

        api_url = '{0}coins/{1}/ohlc?vs_currency={2}&days={3}'.format(self.api_base_url, id, vs_currency, days)
        api_url = self.__api_url_params(api_url, kwargs, api_url_has_params=True)

        return self.__request(api_url)

    # ---------- Contract ----------#
    @func_args_preprocessing
    def get_coin_info_from_contract_address_by_id(self, id, contract_address, **kwargs):
        """Get coin info from contract address"""

        api_url = '{0}coins/{1}/contract/{2}'.format(self.api_base_url, id, contract_address)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coin_market_chart_from_contract_address_by_id(self, id, contract_address, vs_currency, days, **kwargs):
        """Get historical market data include price, market cap, and 24h volume (granularity auto) from a contract address"""

        api_url = '{0}coins/{1}/contract/{2}/market_chart/?vs_currency={3}&days={4}'.format(self.api_base_url, id,
                                                                                            contract_address,
                                                                                            vs_currency, days)
        api_url = self.__api_url_params(api_url, kwargs, api_url_has_params=True)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coin_market_chart_range_from_contract_address_by_id(self, id, contract_address, vs_currency, from_timestamp,
                                                                to_timestamp, **kwargs):
        """Get historical market data include price, market cap, and 24h volume within a range of timestamp (granularity auto) from a contract address"""

        api_url = '{0}coins/{1}/contract/{2}/market_chart/range?vs_currency={3}&from={4}&to={5}'.format(
            self.api_base_url, id, contract_address, vs_currency, from_timestamp, to_timestamp)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- ASSET PLATFORMS ----------#
    @func_args_preprocessing
    def get_asset_platforms(self, **kwargs):
        """List all asset platforms (Blockchain networks)"""

        api_url = '{0}asset_platforms'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- CATEGORIES ----------#
    @func_args_preprocessing
    def get_coins_categories_list(self, **kwargs):
        """List all categories"""

        api_url = '{0}coins/categories/list'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_coins_categories(self, **kwargs):
        """List all categories with market data"""

        api_url = '{0}coins/categories'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- EXCHANGES ----------#
    @func_args_preprocessing
    def get_exchanges_list(self, **kwargs):
        """List all exchanges"""

        api_url = '{0}exchanges'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_exchanges_id_name_list(self, **kwargs):
        """List all supported markets id and name (no pagination required)"""

        api_url = '{0}exchanges/list'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_exchanges_by_id(self, id, **kwargs):
        """Get exchange volume in BTC and tickers"""

        api_url = '{0}exchanges/{1}'.format(self.api_base_url, id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_exchanges_tickers_by_id(self, id, **kwargs):
        """Get exchange tickers (paginated, 100 tickers per page)"""

        api_url = '{0}exchanges/{1}/tickers'.format(self.api_base_url, id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_exchanges_status_updates_by_id(self, id, **kwargs):
        """Get status updates for a given exchange"""

        api_url = '{0}exchanges/{1}/status_updates'.format(self.api_base_url, id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_exchanges_volume_chart_by_id(self, id, days, **kwargs):
        """Get volume chart data for a given exchange"""

        kwargs['days'] = days

        api_url = '{0}exchanges/{1}/volume_chart'.format(self.api_base_url, id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- FINANCE ----------#
    @func_args_preprocessing
    def get_finance_platforms(self, **kwargs):
        """Get cryptocurrency finance platforms data"""

        api_url = '{0}finance_platforms'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_finance_products(self, **kwargs):
        """Get cryptocurrency finance products data"""

        api_url = '{0}finance_products'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- INDEXES ----------#
    @func_args_preprocessing
    def get_indexes(self, **kwargs):
        """List all market indexes"""

        api_url = '{0}indexes'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # @func_args_preprocessing
    # def get_indexes_by_id(self, id, **kwargs):
    #    """Get market index by id"""
    #
    #    api_url = '{0}indexes/{1}'.format(self.api_base_url, id)
    #    api_url = self.__api_url_params(api_url, kwargs)
    #
    #    return self.__request(api_url)

    @func_args_preprocessing
    def get_indexes_by_market_id_and_index_id(self, market_id, id, **kwargs):
        """Get market index by market id and index id"""

        api_url = '{0}indexes/{1}/{2}'.format(self.api_base_url, market_id, id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_indexes_list(self, **kwargs):
        """List market indexes id and name"""

        api_url = '{0}indexes/list'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- DERIVATIVES ----------#
    @func_args_preprocessing
    def get_derivatives(self, **kwargs):
        """List all derivative tickers"""

        api_url = '{0}derivatives'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_derivatives_exchanges(self, **kwargs):
        """List all derivative tickers"""

        api_url = '{0}derivatives/exchanges'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_derivatives_exchanges_by_id(self, id, **kwargs):
        """List all derivative tickers"""

        api_url = '{0}derivatives/exchanges/{1}'.format(self.api_base_url, id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_derivatives_exchanges_list(self, **kwargs):
        """List all derivative tickers"""

        api_url = '{0}derivatives/exchanges/list'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- STATUS UPDATES ----------#
    @func_args_preprocessing
    def get_status_updates(self, **kwargs):
        """List all status_updates with data (description, category, created_at, user, user_title and pin)"""

        api_url = '{0}status_updates'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- EVENTS ----------#
    @func_args_preprocessing
    def get_events(self, **kwargs):
        """Get events, paginated by 100"""

        api_url = '{0}events'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_events_countries(self, **kwargs):
        """Get list of event countries"""

        api_url = '{0}events/countries'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    @func_args_preprocessing
    def get_events_types(self, **kwargs):
        """Get list of event types"""

        api_url = '{0}events/types'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- EXCHANGE-RATES ----------#
    @func_args_preprocessing
    def get_exchange_rates(self, **kwargs):
        """Get BTC-to-Currency exchange rates"""

        api_url = '{0}exchange_rates'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- TRENDING ----------#
    @func_args_preprocessing
    def get_search_trending(self, **kwargs):
        """Get top 7 trending coin searches"""

        api_url = '{0}search/trending'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)

    # ---------- GLOBAL ----------#
    @func_args_preprocessing
    def get_global(self, **kwargs):
        """Get cryptocurrency global data"""

        api_url = '{0}global'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)['data']

    @func_args_preprocessing
    def get_global_decentralized_finance_defi(self, **kwargs):
        """Get cryptocurrency global decentralized finance(defi) data"""

        api_url = '{0}global/decentralized_finance_defi'.format(self.api_base_url)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)['data']

    # ---------- COMPANIES ----------#
    @func_args_preprocessing
    def get_companies_public_treasury_by_coin_id(self, coin_id, **kwargs):
        """Get public companies data"""

        api_url = '{0}companies/public_treasury/{1}'.format(self.api_base_url, coin_id)
        api_url = self.__api_url_params(api_url, kwargs)

        return self.__request(api_url)


    @func_args_preprocessing
    def get_onchain_top_pools(self, network: str, max_pages: int):
        url = f'{self.api_base_url}/onchain/networks/{network}/pools'
        all_pools = {}
        page = 1
        while True:
            params = {
                "page": page,
                "sort": "h24_volume_usd_desc",
            }

            api_url = self.__api_url_params(url, params)

            response = self.__request(api_url)

            pools = response.get("data", [])

            # Break the loop if there are no more pools
            if not pools:
                break

            all_pools.update({pool["id"]: pool for pool in pools})

            # Move to the next page
            page += 1

            # take just first N pages
            if page >= max_pages:
                break

        return all_pools

    def get_onchain_dex_pools(self, network: str, dex: str, max_pages: int = None, max_pools: int = None,
                              sort: str = 'h24_volume_usd_desc', include: str = 'base_token,quote_token,dex'):
        """Return paginated pools for one DEX, together with included token metadata.

        ``max_pages`` and ``max_pools`` are optional safety limits. With neither set,
        pagination continues until CoinGecko returns an empty page.
        """
        if not isinstance(network, str) or not network:
            raise ValueError('network must be a non-empty string')
        if not isinstance(dex, str) or not dex:
            raise ValueError('dex must be a non-empty string')
        if max_pages is not None and (not isinstance(max_pages, int) or isinstance(max_pages, bool) or max_pages <= 0):
            raise ValueError('max_pages must be a positive integer or None')
        if max_pools is not None and (not isinstance(max_pools, int) or isinstance(max_pools, bool) or max_pools <= 0):
            raise ValueError('max_pools must be a positive integer or None')

        url = f'{self.api_base_url.rstrip("/")}/onchain/networks/{network}/dexes/{dex}/pools'
        pools = []
        included = {}
        seen_pool_ids = set()
        page = 1
        pages_fetched = 0
        complete = False
        stop_reason = None
        request_error = None
        failed_page = None

        while max_pages is None or page <= max_pages:
            params = {'page': page, 'sort': sort, 'include': include}
            try:
                response = self.__request_onchain_page(self.__api_url_params(url, params))
            except requests.exceptions.RequestException as error:
                stop_reason = 'request_error'
                failed_page = page
                request_error = str(error)
                break
            pages_fetched += 1
            page_pools = response.get('data', [])

            if not page_pools:
                complete = True
                stop_reason = 'empty_page'
                break

            new_pool_count = 0
            for pool in page_pools:
                pool_id = pool.get('id')
                if pool_id in seen_pool_ids:
                    continue
                seen_pool_ids.add(pool_id)
                pools.append(pool)
                new_pool_count += 1
                if max_pools is not None and len(pools) >= max_pools:
                    pools = pools[:max_pools]
                    stop_reason = 'max_pools'
                    break

            for item in response.get('included', []):
                item_id = item.get('id')
                if item_id:
                    included[item_id] = item

            if stop_reason == 'max_pools':
                break
            if new_pool_count == 0:
                stop_reason = 'repeated_page'
                break
            page += 1

        if stop_reason is None:
            stop_reason = 'max_pages'

        return {
            'data': pools,
            'included': list(included.values()),
            'meta': {
                'network': network,
                'dex': dex,
                'pages_fetched': pages_fetched,
                'pool_count': len(pools),
                'complete': complete,
                'stop_reason': stop_reason,
                'failed_page': failed_page,
                'request_error': request_error,
            },
        }

    def get_onchain_network_pools(self, network: str, max_pages: int = None, max_pools: int = None,
                                  sort: str = 'h24_volume_usd_desc', include: str = 'base_token,quote_token,dex'):
        """Return paginated pools across a network, using the same result shape as DEX pool discovery."""
        return self.__get_onchain_pools(network, 'pools', max_pages, max_pools, sort, include)

    def get_onchain_token_pools(self, network: str, address: str, max_pages: int = None,
                                max_pools: int = None, sort: str = 'h24_volume_usd_desc',
                                include: str = 'base_token,quote_token,dex'):
        """Return pools for an exact token address, retaining pagination/error metadata."""
        if not isinstance(address, str) or not address or any(c in address for c in '/?#'):
            raise ValueError('address must be a non-empty token address')
        result = self.__get_onchain_pools(
            network, f'tokens/{address}/pools', max_pages, max_pools, sort, include)
        result['meta']['token_address'] = address
        return result

    def __get_onchain_pools(self, network, resource, max_pages, max_pools, sort, include):
        if not isinstance(network, str) or not network:
            raise ValueError('network must be a non-empty string')
        if max_pages is not None and (not isinstance(max_pages, int) or isinstance(max_pages, bool) or max_pages <= 0):
            raise ValueError('max_pages must be a positive integer or None')
        if max_pools is not None and (not isinstance(max_pools, int) or isinstance(max_pools, bool) or max_pools <= 0):
            raise ValueError('max_pools must be a positive integer or None')

        url = f'{self.api_base_url.rstrip("/")}/onchain/networks/{network}/{resource}'
        pools = []
        included = {}
        seen_pool_ids = set()
        page = 1
        pages_fetched = 0
        complete = False
        stop_reason = None
        request_error = None
        failed_page = None

        while max_pages is None or page <= max_pages:
            try:
                response = self.__request_onchain_page(self.__api_url_params(url, {
                    'page': page, 'sort': sort, 'include': include}))
            except (requests.exceptions.RequestException, ValueError) as error:
                stop_reason = 'request_error'
                failed_page = page
                request_error = str(error)
                break
            pages_fetched += 1
            page_pools = response.get('data', [])
            if not page_pools:
                complete = True
                stop_reason = 'empty_page'
                break

            new_pool_count = 0
            for pool in page_pools:
                pool_id = pool.get('id')
                if pool_id in seen_pool_ids:
                    continue
                seen_pool_ids.add(pool_id)
                pools.append(pool)
                new_pool_count += 1
                if max_pools is not None and len(pools) >= max_pools:
                    pools = pools[:max_pools]
                    stop_reason = 'max_pools'
                    break

            for item in response.get('included', []):
                if item.get('id'):
                    included[item['id']] = item

            if stop_reason == 'max_pools':
                break
            if new_pool_count == 0:
                stop_reason = 'repeated_page'
                break
            page += 1

        if stop_reason is None:
            stop_reason = 'max_pages'

        return {
            'data': pools,
            'included': list(included.values()),
            'meta': {
                'network': network,
                'pages_fetched': pages_fetched,
                'pool_count': len(pools),
                'complete': complete,
                'stop_reason': stop_reason,
                'failed_page': failed_page,
                'request_error': request_error,
            },
        }
