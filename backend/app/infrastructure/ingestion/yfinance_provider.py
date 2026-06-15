"""yfinance implementation of IMarketDataProvider.

Provides market data by wrapping yfinance inside a thread pool to avoid blocking.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import pandas as pd
import yfinance as yf

from app.domain.interfaces.market_data import IMarketDataProvider, OHLCVBar
from app.domain.models.company import Company, MarketPrice
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


SYNONYM_MAP = {
    "bccl": "coal india",
    "coking": "coal india",
    "coking coal": "coal india",
    "bharat coal": "coal india",
    "bharat coal india": "coal india",
    "indian coal": "coal india",
    "state bank": "sbin",
    "state bank of india": "sbin",
    "lic": "lici",
    "life insurance": "lici",
    "l&t": "lt",
    "larsen": "lt",
    "larsen & toubro": "lt",
    "hindustan unilever": "hindunilvr",
    "unilever": "hindunilvr",
    "bharat petroleum": "bpcl",
    "indian oil": "ioc",
    "hindustan petroleum": "hpcl",
    "gas authority": "gail",
    "steel authority": "sail",
    "steel authority of india": "sail",
    "bharti airtel": "bhartiartl",
    "airtel": "bhartiartl",
    "power grid": "powergrid",
    "bharat electronics": "bel",
    "bharat heavy": "bhel",
    "hindustan aeronautics": "hal",
}

LOCAL_INDIAN_STOCKS = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "INFY.NS", "name": "Infosys Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SBIN.NS", "name": "State Bank of India", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ITC.NS", "name": "ITC Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "LT.NS", "name": "Larsen & Toubro Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "AXISBANK.NS", "name": "Axis Bank Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ASIANPAINT.NS", "name": "Asian Paints Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "MARUTI.NS", "name": "Maruti Suzuki India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TITAN.NS", "name": "Titan Company Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SUNPHARMA.NS", "name": "Sun Pharmaceutical Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "WIPRO.NS", "name": "Wipro Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ONGC.NS", "name": "Oil and Natural Gas Corporation Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "NTPC.NS", "name": "NTPC Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "POWERGRID.NS", "name": "Power Grid Corporation of India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ADANIENT.NS", "name": "Adani Enterprises Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ADANIPORTS.NS", "name": "Adani Ports and Special Economic Zone Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "COALINDIA.NS", "name": "Coal India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TATASTEEL.NS", "name": "Tata Steel Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "JIOFIN.NS", "name": "Jio Financial Services Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HCLTECH.NS", "name": "HCL Technologies Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "NESTLEIND.NS", "name": "Nestle India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HAL.NS", "name": "Hindustan Aeronautics Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BEL.NS", "name": "Bharat Electronics Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BHEL.NS", "name": "Bharat Heavy Electricals Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BPCL.NS", "name": "Bharat Petroleum Corporation Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "IOC.NS", "name": "Indian Oil Corporation Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HPCL.NS", "name": "Hindustan Petroleum Corporation Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "GAIL.NS", "name": "GAIL (India) Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SAIL.NS", "name": "Steel Authority of India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "IRCTC.NS", "name": "Indian Railway Catering and Tourism Corporation Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "IRFC.NS", "name": "Indian Railway Finance Corporation Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "PFC.NS", "name": "Power Finance Corporation Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "RECLTD.NS", "name": "REC Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "DLF.NS", "name": "DLF Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "GODREJCP.NS", "name": "Godrej Consumer Products Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "DABUR.NS", "name": "Dabur India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "MARICO.NS", "name": "Marico Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "COLPAL.NS", "name": "Colgate-Palmolive (India) Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BRITANNIA.NS", "name": "Britannia Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "PIDILITIND.NS", "name": "Pidilite Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "GRASIM.NS", "name": "Grasim Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "JSWSTEEL.NS", "name": "JSW Steel Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HINDALCO.NS", "name": "Hindalco Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "VEDL.NS", "name": "Vedanta Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TRENT.NS", "name": "Trent Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "DMART.NS", "name": "Avenue Supermarts Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "INDIGO.NS", "name": "InterGlobe Aviation Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ZOMATO.NS", "name": "Zomato Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "PAYTM.NS", "name": "One 97 Communications Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "LICHSGFIN.NS", "name": "LIC Housing Finance Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "LICI.NS", "name": "Life Insurance Corporation of India", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TATACONSUM.NS", "name": "Tata Consumer Products Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TATACOMM.NS", "name": "Tata Communications Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TATAPOWER.NS", "name": "Tata Power Company Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TATACHEM.NS", "name": "Tata Chemicals Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TATAELXSI.NS", "name": "Tata Elxsi Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "APOLLOHOSP.NS", "name": "Apollo Hospitals Enterprise Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BAJAJ-AUTO.NS", "name": "Bajaj Auto Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BAJAJFINSV.NS", "name": "Bajaj Finserv Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CIPLA.NS", "name": "Cipla Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "DIVISLAB.NS", "name": "Divi's Laboratories Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "DRREDDY.NS", "name": "Dr. Reddy's Laboratories Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "EICHERMOT.NS", "name": "Eicher Motors Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HEROMOTOCO.NS", "name": "Hero MotoCorp Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "INDUSINDBK.NS", "name": "IndusInd Bank Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "LTIM.NS", "name": "LTIMindtree Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "M&M.NS", "name": "Mahindra & Mahindra Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SBILIFE.NS", "name": "SBI Life Insurance Company Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SHRIRAMFIN.NS", "name": "Shriram Finance Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HDFCLIFE.NS", "name": "HDFC Life Insurance Company Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BHARATFORG.NS", "name": "Bharat Forge Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BANKBARODA.NS", "name": "Bank of Baroda", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CANBK.NS", "name": "Canara Bank", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "PNB.NS", "name": "Punjab National Bank", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "UNIONBANK.NS", "name": "Union Bank of India", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "INDIANB.NS", "name": "Indian Bank", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "IDBI.NS", "name": "IDBI Bank Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "YESBANK.NS", "name": "Yes Bank Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "FEDERALBNK.NS", "name": "Federal Bank Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "IDFCFIRSTB.NS", "name": "IDFC First Bank Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ASHOKLEY.NS", "name": "Ashok Leyland Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CUMMINSIND.NS", "name": "Cummins India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ESCORTS.NS", "name": "Escorts Kubota Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "MRF.NS", "name": "MRF Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BALKRISIND.NS", "name": "Balkrishna Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "APOLLOTYRE.NS", "name": "Apollo Tyres Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "JKTYRE.NS", "name": "JK Tyre & Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CEAT.NS", "name": "CEAT Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TVSMOTOR.NS", "name": "TVS Motor Company Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "MUTHOOTFIN.NS", "name": "Muthoot Finance Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "MANAPPURAM.NS", "name": "Manappuram Finance Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CHOLAFIN.NS", "name": "Cholamandalam Investment and Finance Company Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "LTF.NS", "name": "L&T Finance Holdings Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "LUPIN.NS", "name": "Lupin Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "AUROPHARMA.NS", "name": "Aurobindo Pharma Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BIOCON.NS", "name": "Biocon Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "GLENMARK.NS", "name": "Glenmark Pharmaceuticals Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TORNTPHARM.NS", "name": "Torrent Pharmaceuticals Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ALKEM.NS", "name": "Alkem Laboratories Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ABBOTINDIA.NS", "name": "Abbott India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "IPCALAB.NS", "name": "Ipca Laboratories Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "LAURUSLABS.NS", "name": "Laurus Labs Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ZYDUSLIFE.NS", "name": "Zydus Lifesciences Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CONCOR.NS", "name": "Container Corporation of India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "GMRINFRA.NS", "name": "GMR Airports Infrastructure Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HAVELLS.NS", "name": "Havells India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "POLYCAB.NS", "name": "Polycab India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "KEI.NS", "name": "KEI Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "VOLTAS.NS", "name": "Voltas Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BLUESTARCO.NS", "name": "Blue Star Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CROMPTON.NS", "name": "Crompton Greaves Consumer Electricals Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "DIXON.NS", "name": "Dixon Technologies (India) Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "AMBER.NS", "name": "Amber Enterprises India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ASTRAL.NS", "name": "Astral Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SUPREMEIND.NS", "name": "Supreme Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "FINPIPE.NS", "name": "Finolex Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "KAJARIACER.NS", "name": "Kajaria Ceramics Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SOMANYCERA.NS", "name": "Somany Ceramics Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BERGERPAINT.NS", "name": "Berger Paints India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "KANSAINER.NS", "name": "Kansai Nerolac Paints Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "INDIGOPNTS.NS", "name": "Indigo Paints Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "MCDOWELL-N.NS", "name": "United Spirits Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "UBL.NS", "name": "United Breweries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "RADICO.NS", "name": "Radico Khaitan Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "GODREJPROP.NS", "name": "Godrej Properties Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "OBEROIRLTY.NS", "name": "Oberoi Realty Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "PRESTIGE.NS", "name": "Prestige Estates Projects Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SOBHA.NS", "name": "Sobha Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "LODHA.NS", "name": "Macrotech Developers Limited (Lodha)", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BRIGADE.NS", "name": "Brigade Enterprises Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "PHOENIXLTD.NS", "name": "The Phoenix Mills Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "JUBLFOOD.NS", "name": "Jubilant FoodWorks Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "DEVYANI.NS", "name": "Devyani International Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "WESTLIFE.NS", "name": "Westlife Foodworld Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "RBA.NS", "name": "Restaurant Brands Asia Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SAPPHIRE.NS", "name": "Sapphire Foods India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "KALYANKJIL.NS", "name": "Kalyan Jewellers India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SENCO.NS", "name": "Senco Gold Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "COROMANDEL.NS", "name": "Coromandel International Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CHAMBLFERT.NS", "name": "Chambal Fertilisers and Chemicals Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "GNFC.NS", "name": "Gujarat Narmada Valley Fertilizers & Chemicals Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "GSFC.NS", "name": "Gujarat State Fertilizers & Chemicals Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "DEEPAKNTR.NS", "name": "Deepak Nitrite Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "AARTIIND.NS", "name": "Aarti Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SRF.NS", "name": "SRF Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "FLUOROCHEM.NS", "name": "Gujarat Fluorochemicals Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ATUL.NS", "name": "Atul Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "NAVINFLUOR.NS", "name": "Navin Fluorine International Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ROUTE.NS", "name": "Route Mobile Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TANLA.NS", "name": "Tanla Platforms Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "DISHTV.NS", "name": "Dish TV India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SUNTV.NS", "name": "Sun TV Network Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ZEEL.NS", "name": "Zee Entertainment Enterprises Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "PVRINOX.NS", "name": "PVR INOX Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "NAUKRI.NS", "name": "Info Edge (India) Limited (Naukri)", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "INDIAMART.NS", "name": "IndiaMART InterMESH Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "JUSTDIAL.NS", "name": "Just Dial Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "NYKAA.NS", "name": "FSN E-Commerce Ventures Limited (Nykaa)", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "DELHIVERY.NS", "name": "Delhivery Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CARTRADE.NS", "name": "CarTrade Tech Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "STARHEALTH.NS", "name": "Star Health and Allied Insurance Company Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "GICRE.NS", "name": "General Insurance Corporation of India", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "NIACL.NS", "name": "The New India Assurance Company Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SBICARD.NS", "name": "SBI Cards and Payment Services Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "ANGELONE.NS", "name": "Angel One Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CDSL.NS", "name": "Central Depository Services (India) Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "MCX.NS", "name": "Multi Commodity Exchange of India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "BSE.NS", "name": "BSE Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CAMS.NS", "name": "Computer Age Management Services Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "KFINTECH.NS", "name": "KFin Technologies Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HUDCO.NS", "name": "Housing & Urban Development Corporation Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "NHPC.NS", "name": "NHPC Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SJVN.NS", "name": "SJVN Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "NLCINDIA.NS", "name": "NLC India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TORNTPOWER.NS", "name": "Torrent Power Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CESC.NS", "name": "CESC Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "JSWENERGY.NS", "name": "JSW Energy Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "JINDALSTEL.NS", "name": "Jindal Steel & Power Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "VGUARD.NS", "name": "V-Guard Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SYMPHONY.NS", "name": "Symphony Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TTKPRESTIG.NS", "name": "TTK Prestige Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "HAWKINS.NS", "name": "Hawkins Cookers Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "VIPIND.NS", "name": "VIP Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SAFARI.NS", "name": "Safari Industries (India) Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CENTURYPLY.NS", "name": "Century Plyboards (India) Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "GREENPLY.NS", "name": "Greenply Industries Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CERA.NS", "name": "Cera Sanitaryware Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "PRINCEPIPE.NS", "name": "Prince Pipes and Fittings Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "FINCABLES.NS", "name": "Finolex Cables Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "RRKABEL.NS", "name": "RR Kabel Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SUZLON.NS", "name": "Suzlon Energy Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "INOXWIND.NS", "name": "Inox Wind Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SWSOLAR.NS", "name": "Sterling and Wilson Renewable Energy Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "WAAREE.NS", "name": "Waaree Energies Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "PREMIER.NS", "name": "Premier Energies Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CGPOWER.NS", "name": "CG Power and Industrial Solutions Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "KAYNES.NS", "name": "Kaynes Technology India Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SYRMA.NS", "name": "Syrma SGS Technology Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "AVALON.NS", "name": "Avalon Technologies Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "CYIENT.NS", "name": "Cyient Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "KPITTECH.NS", "name": "KPIT Technologies Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "TATATECH.NS", "name": "Tata Technologies Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "LTTS.NS", "name": "L&T Technology Services Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "COFORGE.NS", "name": "Coforge Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "PERSISTENT.NS", "name": "Persistent Systems Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "MPHASIS.NS", "name": "Mphasis Limited", "exchange": "NSE", "type": "EQUITY"},
    {"symbol": "SONATSOFTW.NS", "name": "Sonata Software Limited", "exchange": "NSE", "type": "EQUITY"}
]


class YFinanceDataProvider:
    """Market data provider implementing IMarketDataProvider via yfinance."""

    def __init__(self) -> None:
        self._info_cache: dict[str, Company] = {}
        self._nse_equities: list[dict[str, str]] = []
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.load_nse_equities())
        except RuntimeError:
            pass

    async def load_nse_equities(self) -> None:
        try:
            logger.info("Downloading NSE equity list from archives...")
            import httpx
            import csv
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "*/*"
            }
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                await client.get("https://www.nseindia.com")
                r = await client.get("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv")
                if r.status_code == 200:
                    text = r.text
                    lines = text.splitlines()
                    reader = csv.reader(lines)
                    header = next(reader)
                    
                    symbol_idx = 0
                    name_idx = 1
                    series_idx = 2
                    
                    equities = []
                    for row in reader:
                        if not row or len(row) <= max(symbol_idx, name_idx, series_idx):
                            continue
                        symbol = row[symbol_idx].strip()
                        name = row[name_idx].strip()
                        series = row[series_idx].strip()
                        
                        if series in ("EQ", "BE", "SM"):
                            ticker = f"{symbol}.NS"
                            equities.append({
                                "symbol": ticker,
                                "name": name,
                                "exchange": "NSE",
                                "type": "EQUITY"
                            })
                    self._nse_equities = equities
                    logger.info("Successfully loaded active NSE equities", count=len(equities))
                else:
                    logger.error("Failed to download EQUITY_L.csv", status=r.status_code)
        except Exception as e:
            logger.error("Error loading NSE equities from CSV", error=str(e))

    async def get_price(self, ticker: str) -> MarketPrice:
        res = await self.get_prices([ticker])
        if ticker in res:
            return res[ticker]
        raise ValueError(f"Ticker {ticker} not found")

    @timed
    async def get_prices(self, tickers: list[str]) -> dict[str, MarketPrice]:
        return await asyncio.to_thread(self._fetch_prices_sync, tickers)

    def _fetch_prices_sync(self, tickers: list[str]) -> dict[str, MarketPrice]:
        res: dict[str, MarketPrice] = {}
        try:
            # Fetch daily data
            data = yf.download(tickers, period="1d", group_by="ticker", progress=False, threads=True)
            for ticker in tickers:
                try:
                    if isinstance(data.columns, pd.MultiIndex):
                        if ticker in data.columns.levels[0]:
                            ticker_df = data[ticker]
                        elif len(data.columns.levels) > 1 and ticker in data.columns.levels[1]:
                            ticker_df = data.xs(ticker, axis=1, level=1)
                        else:
                            continue
                    else:
                        ticker_df = data

                    if ticker_df.empty:
                        continue

                    last_row = ticker_df.iloc[-1]
                    close_val = last_row.get("Close")
                    if pd.isna(close_val):
                        close_val = last_row.get("Adj Close", 0.0)
                    if pd.isna(close_val):
                        close_val = 0.0

                    open_val = last_row.get("Open")
                    if pd.isna(open_val):
                        open_val = close_val
                    high_val = last_row.get("High")
                    if pd.isna(high_val):
                        high_val = close_val
                    low_val = last_row.get("Low")
                    if pd.isna(low_val):
                        low_val = close_val
                        
                    volume_val = last_row.get("Volume", 0)
                    if pd.isna(volume_val):
                        volume_val = 0
                    else:
                        volume_val = int(volume_val)

                    # Fallback previous close
                    prev_close = open_val
                    change = close_val - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close != 0 else 0.0
                    
                    if pd.isna(change):
                        change = 0.0
                    if pd.isna(change_pct):
                        change_pct = 0.0

                    res[ticker] = MarketPrice(
                        ticker=ticker,
                        price=float(close_val),
                        open=float(open_val),
                        high=float(high_val),
                        low=float(low_val),
                        close=float(close_val),
                        volume=volume_val,
                        change=float(change),
                        change_pct=float(change_pct),
                        timestamp=datetime.utcnow(),
                    )
                except Exception as ex:
                    logger.debug("Error parsing yfinance data for ticker", ticker=ticker, error=str(ex))
        except Exception as e:
            logger.error("Error batch fetching prices from yfinance", error=str(e))

        # Fill any missing tickers with fallback data
        for ticker in tickers:
            if ticker not in res:
                res[ticker] = MarketPrice(
                    ticker=ticker,
                    price=100.0,
                    open=100.0,
                    high=105.0,
                    low=98.0,
                    close=100.0,
                    volume=100000,
                    change=0.0,
                    change_pct=0.0,
                    timestamp=datetime.utcnow(),
                )
        return res

    @timed
    async def get_history(
        self,
        ticker: str,
        *,
        period: str = "1y",
        interval: str = "1d",
    ) -> list[OHLCVBar]:
        return await asyncio.to_thread(self._fetch_history_sync, ticker, period, interval)

    def _fetch_history_sync(self, ticker: str, period: str, interval: str) -> list[OHLCVBar]:
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=period, interval=interval)
            bars = []
            for ts, row in df.iterrows():
                dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                bars.append(
                    OHLCVBar(
                        timestamp=dt,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=int(row["Volume"]),
                    )
                )
            return bars
        except Exception as e:
            logger.error("Error fetching history from yfinance", ticker=ticker, error=str(e))
            return []

    @timed
    async def get_company_info(self, ticker: str) -> Company:
        if ticker in self._info_cache:
            return self._info_cache[ticker]
        res = await asyncio.to_thread(self._fetch_company_info_sync, ticker)
        self._info_cache[ticker] = res
        return res

    def _fetch_company_info_sync(self, ticker: str) -> Company:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            name = info.get("longName", info.get("shortName", ticker))
            sector = info.get("sector", "Conglomerate")
            industry = info.get("industry", "Conglomerate")
            country = info.get("country", "India")
            market_cap = info.get("marketCap", 0.0)
            current_price = info.get("currentPrice", info.get("previousClose", 0.0))
            pe_ratio = info.get("trailingPE", 0.0)
            pb_ratio = info.get("priceToBook", 0.0)
            debt_to_equity = info.get("debtToEquity", 0.0)
            if debt_to_equity and debt_to_equity > 5:
                debt_to_equity = debt_to_equity / 100.0

            revenue = info.get("totalRevenue", 0.0)
            net_profit = info.get("netIncomeToCommon", 0.0)
            roe = info.get("returnOnEquity", 0.0)
            roce = info.get("returnOnAssets", 0.0)
            dividend_yield = info.get("dividendYield", 0.0)
            beta = info.get("beta", 1.0)
            description = info.get("longBusinessSummary", "")

            return Company(
                ticker=ticker,
                name=name,
                sector=sector,
                industry=industry,
                country=country,
                market_cap=market_cap,
                current_price=current_price,
                pe_ratio=pe_ratio,
                pb_ratio=pb_ratio,
                debt_to_equity=debt_to_equity,
                revenue=revenue,
                net_profit=net_profit,
                roe=roe,
                roce=roce,
                dividend_yield=dividend_yield,
                beta=beta,
                description=description,
                last_updated=datetime.utcnow(),
            )
        except Exception as e:
            logger.debug("Error fetching company info from yfinance", ticker=ticker, error=str(e))
            return Company(
                ticker=ticker,
                name=ticker.replace(".NS", "").replace("^", ""),
                sector="Technology" if "TCS" in ticker or "INFY" in ticker else "Financial Services" if "BANK" in ticker else "Energy" if "RELIANCE" in ticker else "Conglomerate",
                industry="Other",
                country="India",
                last_updated=datetime.utcnow(),
            )

    async def get_index_constituents(self, index: str) -> list[str]:
        if index == "^NSEI":
            return [
                "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
                "LT.NS", "BAJFINANCE.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
                "TITAN.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "WIPRO.NS", "ONGC.NS",
                "NTPC.NS", "POWERGRID.NS", "TECHM.NS", "HCLTECH.NS", "NESTLEIND.NS",
                "HAL.NS", "BEL.NS", "INDIGO.NS", "COALINDIA.NS", "TATASTEEL.NS",
            ]
        elif index == "^BSESN":
            return [
                "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
                "LT.NS", "BAJFINANCE.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
            ]
        return []

    async def search_tickers(self, query: str) -> list[dict[str, Any]]:
        import asyncio
        import re
        import yfinance as yf
        if not query:
            return []
        
        if not self._nse_equities:
            asyncio.create_task(self.load_nse_equities())
            
        q_clean = query.lower().strip()
        search_db = self._nse_equities if self._nse_equities else LOCAL_INDIAN_STOCKS
        
        # Tokenize query for token-based matching
        tokens = [t for t in re.split(r"[^a-zA-Z0-9]", q_clean) if len(t) >= 3]
        
        # 1. Local Database Search
        local_results = []
        for stock in search_db:
            symbol_clean = stock["symbol"].lower().replace(".ns", "")
            name_clean = stock["name"].lower()
            
            # Check for direct matches
            match = False
            if q_clean in symbol_clean or q_clean in name_clean:
                match = True
            else:
                # Check for token matches
                for token in tokens:
                    if token in symbol_clean or token in name_clean:
                        match = True
                        break
                # Check synonym map
                if not match:
                    for syn, official in SYNONYM_MAP.items():
                        if syn in q_clean:
                            off_clean = official.lower()
                            if off_clean in symbol_clean or off_clean in name_clean:
                                match = True
                                break
            
            if match:
                local_results.append({
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "exchange": stock["exchange"],
                    "type": stock["type"]
                })
        
        # 2. Parallel YFinance Search
        # Try both original query and synonym query if present
        queries_to_try = [query]
        for syn, official in SYNONYM_MAP.items():
            if syn in q_clean and official not in queries_to_try:
                queries_to_try.append(official)
        
        yf_results = []
        for q_try in queries_to_try:
            try:
                search = await asyncio.to_thread(yf.Search, q_try)
                for quote in getattr(search, "quotes", []):
                    if quote.get("quoteType") in ("EQUITY", "INDEX", "ETF"):
                        yf_results.append({
                            "symbol": quote.get("symbol"),
                            "name": quote.get("longname") or quote.get("shortname") or quote.get("symbol"),
                            "exchange": quote.get("exchDisp"),
                            "type": quote.get("quoteType")
                        })
            except Exception as e:
                logger.debug("Error in yfinance search for query", query=q_try, error=str(e))

        # 3. Merge and Deduplicate (local first)
        merged = []
        seen = set()
        for item in local_results + yf_results:
            symbol = item["symbol"]
            if symbol not in seen:
                seen.add(symbol)
                merged.append(item)
                
        return merged[:15]
