"""
Options pricing and Greeks calculations using Black-Scholes model
"""
import math
from datetime import date, datetime
from typing import Tuple, Optional


def normal_cdf(x: float) -> float:
    """Cumulative distribution function for standard normal distribution"""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def normal_pdf(x: float) -> float:
    """Probability density function for standard normal distribution"""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def black_scholes_greeks(
    spot_price: float,
    strike_price: float,
    time_to_expiry: float,
    risk_free_rate: float = 0.05,
    volatility: float = 0.25,
    option_type: str = "call"
) -> Tuple[float, float, float, float, float]:
    """
    Calculate Black-Scholes option price and Greeks
    
    Args:
        spot_price: Current price of underlying asset
        strike_price: Strike price of option
        time_to_expiry: Time to expiry in years
        risk_free_rate: Risk-free interest rate (default 5%)
        volatility: Implied volatility (default 25%)
        option_type: "call" or "put"
    
    Returns:
        Tuple of (option_price, delta, gamma, theta, vega)
    """
    if time_to_expiry <= 0:
        # Expired option
        if option_type.lower() == "call":
            intrinsic = max(0, spot_price - strike_price)
        else:
            intrinsic = max(0, strike_price - spot_price)
        return intrinsic, 0.0, 0.0, 0.0, 0.0
    
    # Calculate d1 and d2
    d1 = (math.log(spot_price / strike_price) + 
          (risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / (volatility * math.sqrt(time_to_expiry))
    d2 = d1 - volatility * math.sqrt(time_to_expiry)
    
    # Calculate Greeks
    N_d1 = normal_cdf(d1)
    N_d2 = normal_cdf(d2)
    n_d1 = normal_pdf(d1)
    
    if option_type.lower() == "call":
        # Call option
        option_price = spot_price * N_d1 - strike_price * math.exp(-risk_free_rate * time_to_expiry) * N_d2
        delta = N_d1
        theta = (-spot_price * n_d1 * volatility / (2 * math.sqrt(time_to_expiry)) 
                - risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiry) * N_d2) / 365
    else:
        # Put option
        option_price = strike_price * math.exp(-risk_free_rate * time_to_expiry) * normal_cdf(-d2) - spot_price * normal_cdf(-d1)
        delta = N_d1 - 1
        theta = (-spot_price * n_d1 * volatility / (2 * math.sqrt(time_to_expiry)) 
                + risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiry) * normal_cdf(-d2)) / 365
    
    # Common Greeks for both calls and puts
    gamma = n_d1 / (spot_price * volatility * math.sqrt(time_to_expiry))
    vega = spot_price * n_d1 * math.sqrt(time_to_expiry) / 100  # Vega per 1% change in volatility
    
    return option_price, delta, gamma, theta, vega


def parse_option_symbol(symbol: str) -> Tuple[Optional[str], Optional[date], Optional[float], Optional[str]]:
    """
    Parse option symbol to extract underlying, expiry, strike, and option type
    Examples: 
    - "NVDA  250718C00180000" -> ("NVDA", date(2025,7,18), 180.0, "call")
    - "./GCQ5 OGQ5  250728C5000" -> ("GCQ5", date(2025,7,28), 5000.0, "call")
    """
    try:
        print(f"DEBUG: Parsing option symbol: '{symbol}'")
        
        # Handle futures options format: "./GCQ5 OGQ5  250728C5000"
        if symbol.startswith('./'):
            parts = symbol.strip().split()
            if len(parts) >= 3:
                underlying = parts[0][2:]  # Remove "./"
                option_part = parts[2]  # Skip the second part (OGQ5)
                print(f"DEBUG: Futures option - underlying: {underlying}, option_part: {option_part}")
            else:
                return None, None, None, None
        else:
            # Handle equity options format: "NVDA  250718C00180000"
            parts = symbol.strip().split()
            if len(parts) < 2:
                return None, None, None, None
            
            underlying = parts[0]
            option_part = parts[1]
            print(f"DEBUG: Equity option - underlying: {underlying}, option_part: {option_part}")
        
        # Extract date (YYMMDD format)
        if len(option_part) >= 6:
            date_str = option_part[:6]
            year = 2000 + int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            expiry = date(year, month, day)
            print(f"DEBUG: Parsed expiry: {expiry}")
        else:
            print(f"DEBUG: Could not parse date from option_part: {option_part}")
            return underlying, None, None, None
        
        # Extract option type (C/P)
        if len(option_part) >= 7:
            option_type = option_part[6].upper()
            if option_type == 'C':
                option_type = 'call'
            elif option_type == 'P':
                option_type = 'put'
            else:
                print(f"DEBUG: Unrecognized option type: {option_type}")
                return underlying, expiry, None, None
            print(f"DEBUG: Parsed option type: {option_type}")
        else:
            print(f"DEBUG: Could not parse option type from option_part: {option_part}")
            return underlying, expiry, None, None
        
        # Extract strike price 
        if len(option_part) > 7:
            strike_str = option_part[7:]
            # For futures options, strike might not need division by 1000
            if symbol.startswith('./'):
                # Futures strikes are often whole numbers
                strike = float(strike_str)
                # For certain futures, adjust the strike formatting
                if 'GC' in underlying:  # Gold futures
                    strike = strike / 10.0  # Gold prices like 2800 = $2800
                elif 'ZB' in underlying:  # Bond futures  
                    strike = strike / 32.0  # Bond prices in 32nds
                elif 'CL' in underlying:  # Oil futures
                    strike = float(strike_str)  # Oil prices are direct
                elif 'ES' in underlying:  # S&P futures
                    strike = float(strike_str)  # Index prices are direct
                elif 'SI' in underlying:  # Silver futures
                    strike = float(strike_str) / 100.0  # Silver prices
                else:
                    strike = float(strike_str)
            else:
                # Equity options - divide by 1000
                strike = float(strike_str) / 1000.0
            print(f"DEBUG: Parsed strike: {strike}")
        else:
            print(f"DEBUG: Could not parse strike from option_part: {option_part}")
            return underlying, expiry, None, option_type
        
        result = (underlying, expiry, strike, option_type)
        print(f"DEBUG: Final parsed result: {result}")
        return result
        
    except Exception as e:
        print(f"DEBUG: Error parsing option symbol {symbol}: {e}")
        return None, None, None, None


def calculate_option_greeks(
    symbol: str,
    current_price: float,
    strike_price: Optional[float],
    expiry_date: Optional[date],
    option_type: Optional[str],
    volatility: float = 0.25
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate delta and theta for an option position
    
    Args:
        symbol: Option symbol
        current_price: Current underlying price
        strike_price: Strike price of option
        expiry_date: Expiration date
        option_type: "call", "put", "C", or "P"
        volatility: Estimated volatility (default 25%)
    
    Returns:
        Tuple of (delta, theta) or (None, None) if calculation fails
    """
    try:
        # If we don't have parsed option data, try to extract from symbol
        if not all([strike_price, expiry_date, option_type]) and symbol:
            underlying, parsed_expiry, parsed_strike, parsed_type = parse_option_symbol(symbol)
            if not strike_price:
                strike_price = parsed_strike
            if not expiry_date:
                expiry_date = parsed_expiry
            if not option_type:
                option_type = parsed_type
        
        # The current_price from TastyTrade is the option premium, not underlying price
        # We need to estimate the underlying price for Greek calculations
        if strike_price and option_type and expiry_date:
            underlying_price = estimate_underlying_price_from_option_data(
                symbol, current_price, strike_price, option_type, expiry_date
            )
            print(f"DEBUG: Estimated underlying price {underlying_price} from option price {current_price}")
        else:
            underlying_price = current_price
            print(f"DEBUG: Using option price {current_price} as underlying (incomplete option data)")
        
        # Validate inputs
        if not all([current_price, strike_price, expiry_date, option_type]):
            return None, None
        
        if current_price <= 0 or strike_price <= 0:
            return None, None
        
        # Calculate time to expiry
        if isinstance(expiry_date, str):
            expiry_date = datetime.fromisoformat(expiry_date).date()
        
        today = date.today()
        days_to_expiry = (expiry_date - today).days
        
        if days_to_expiry <= 0:
            return 0.0, 0.0
        
        time_to_expiry = days_to_expiry / 365.0
        
        # Normalize option type
        opt_type = option_type.lower()
        if opt_type in ['c', 'call']:
            opt_type = 'call'
        elif opt_type in ['p', 'put']:
            opt_type = 'put'
        else:
            return None, None
        
        # Estimate volatility based on underlying type
        if symbol.startswith('./'):
            # Futures options
            if 'GC' in symbol:  # Gold futures
                volatility = 0.20
            elif 'ZB' in symbol:  # Bond futures
                volatility = 0.15
            elif 'CL' in symbol:  # Oil futures
                volatility = 0.35
            elif 'ES' in symbol:  # S&P E-mini futures
                volatility = 0.18
            elif 'SI' in symbol:  # Silver futures
                volatility = 0.25
            else:
                volatility = 0.25
        elif 'nvda' in symbol.lower():
            volatility = 0.45  # High volatility stock
        elif any(x in symbol.lower() for x in ['spy', 'qqq', 'iwm']):
            volatility = 0.20  # ETF volatility
        else:
            volatility = 0.25  # Default
            
        print(f"DEBUG: Using underlying_price={underlying_price}, volatility={volatility} for {symbol}")
        
        # Calculate Greeks using Black-Scholes
        _, delta, gamma, theta, vega = black_scholes_greeks(
            spot_price=underlying_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            option_type=opt_type
        )
        
        return delta, theta
        
    except Exception as e:
        print(f"DEBUG: Error calculating Greeks for {symbol}: {e}")
        return None, None


def estimate_underlying_price_from_option_data(symbol: str, option_price: float, strike: float, option_type: str, expiry_date) -> float:
    """
    Estimate underlying stock price from option premium using basic approximation
    This is a rough estimate - ideally we'd fetch real underlying prices
    """
    try:
        from datetime import date
        if isinstance(expiry_date, str):
            from datetime import datetime
            expiry_date = datetime.fromisoformat(expiry_date).date()
        
        days_to_expiry = (expiry_date - date.today()).days
        if days_to_expiry <= 0:
            return strike  # Expired option
        
        # Very rough estimation based on option premium and strike
        # This is not accurate but gives us a starting point
        if option_type.lower() == 'call':
            # For calls, underlying is likely strike + premium for ATM options
            estimated_price = strike + (option_price * 10)  # Rough multiplier
        else:
            # For puts, underlying is likely strike - premium for ATM options  
            estimated_price = strike - (option_price * 10)  # Rough multiplier
        
        # Add some market-based estimates for known stocks
        symbol_base = symbol.split()[0] if ' ' in symbol else symbol
        known_prices = {
            'GS': 500,      # Goldman Sachs around $500
            'NVDA': 130,    # NVIDIA around $130  
            'MSFT': 430,    # Microsoft around $430
            'AMZN': 185,    # Amazon around $185
            'PLTR': 40,     # Palantir around $40
            'ARM': 140,     # ARM around $140
            'RDDT': 65,     # Reddit around $65
            'TGT': 155,     # Target around $155
            'QQQ': 485,     # QQQ around $485
            'UNH': 530,     # UnitedHealth around $530
        }
        
        if symbol_base in known_prices:
            return known_prices[symbol_base]
        
        # Fallback to strike price as rough estimate
        return max(estimated_price, strike * 0.5)  # Don't go below 50% of strike
        
    except Exception as e:
        print(f"DEBUG: Error estimating underlying price for {symbol}: {e}")
        return strike  # Fallback to strike price


def estimate_volatility_from_symbol(symbol: str) -> float:
    """
    Estimate implied volatility based on the underlying symbol
    """
    symbol_lower = symbol.lower()
    
    # High volatility stocks
    high_vol_stocks = ['nvda', 'tsla', 'amd', 'meta', 'amzn', 'nflx']
    if any(stock in symbol_lower for stock in high_vol_stocks):
        return 0.50
    
    # Medium volatility stocks
    med_vol_stocks = ['aapl', 'msft', 'googl', 'goog']
    if any(stock in symbol_lower for stock in med_vol_stocks):
        return 0.30
    
    # Low volatility ETFs/indices
    low_vol_etfs = ['spy', 'qqq', 'iwm', 'dia', 'vti', 'bil']
    if any(etf in symbol_lower for etf in low_vol_etfs):
        return 0.18
    
    # Futures (typically medium volatility)
    if symbol.startswith('./'):
        return 0.25
    
    # Default volatility
    return 0.25