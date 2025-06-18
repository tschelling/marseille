import pandas as pd
import numpy as np
import numpy_financial as npf

# --- CONFIGURATION PARAMETERS ---
# You can adjust any of the values in this section to model different scenarios.

PARAMS = {
    # --- Investment Details ---
    "simulation_years": 10,
    "apartment_price": 600000,  # EUR
    "loan_amount": 300000,      # EUR
    "mortgage_term_years": 25,  # Loan amortization period

    # --- Costs & Fees ---
    "buying_costs_pct": 0.07,   # Notary fees, taxes, etc. as a percentage of the price
    "selling_costs_pct": 0.05,  # Real estate agent fees, etc. as a percentage of the final price
    "annual_fixed_costs": 6000, # EUR (condo fees, insurance, property tax, maintenance fund)

    # --- Revenue Details ---
    "tourist_rental_price_per_day": 300, # EUR
    "friends_rental_price_per_day": 50,  # EUR
    "friends_rental_days_per_year": 15,  # Number of days rented to friends/family

    # --- Market Assumptions ---
    "avg_property_value_growth": 0.02, # Annual growth rate for the apartment's value
    "annual_costs_inflation": 0.015,   # Inflation rate for fixed costs
    "base_mortgage_interest_rate": 0.035, # Starting variable interest rate
    "interest_rate_volatility": 0.002,  # Std deviation for random interest rate fluctuations
    
    # --- Analysis Targets ---
    "target_annual_return": 0.05 # The desired annualized return (IRR)
}

def run_simulation(params, tourist_rental_days):
    """
    Runs the financial simulation for the apartment investment over a specified number of years.

    Args:
        params (dict): A dictionary containing all the configuration parameters.
        tourist_rental_days (int): The number of days the apartment is rented to tourists per year.

    Returns:
        tuple: A tuple containing:
            - float: The calculated Internal Rate of Return (IRR) for the investment.
            - pd.DataFrame: A DataFrame with the detailed financial breakdown for each year.
    """

    # --- INITIAL CALCULATIONS ---
    initial_down_payment = params["apartment_price"] - params["loan_amount"]
    buying_costs = params["apartment_price"] * params["buying_costs_pct"]
    total_initial_investment = initial_down_payment + buying_costs

    # This list will hold the full stream of cash flows for the IRR calculation.
    # It starts with the initial cash outflow (the total investment).
    cash_flows = [-total_initial_investment]

    # --- SETUP DATAFRAME FOR YEARLY RESULTS ---
    columns = [
        "Year", "Property Value", "Loan Balance", "Equity", "Rental Revenue",
        "Interest Rate", "Interest Paid", "Principal Paid", "Fixed Costs",
        "Net Cash Flow"
    ]
    simulation_data = []

    # --- INITIALIZE STATE FOR YEAR 0 ---
    remaining_loan = params["loan_amount"]
    current_property_value = params["apartment_price"]
    annual_principal_payment = params["loan_amount"] / params["mortgage_term_years"]
    
    # --- SIMULATION LOOP FOR EACH YEAR ---
    for year in range(1, params["simulation_years"] + 1):
        
        # --- MARKET SHOCKS FOR THE YEAR ---
        # Simulate a variable interest rate for the current year
        interest_rate_shock = np.random.normal(0, params["interest_rate_volatility"])
        current_interest_rate = params["base_mortgage_interest_rate"] + interest_rate_shock
        
        # Appreciate property value
        current_property_value *= (1 + params["avg_property_value_growth"])
        
        # Inflate fixed costs
        current_fixed_costs = params["annual_fixed_costs"] * ((1 + params["annual_costs_inflation"]) ** year)

        # --- CALCULATE ANNUAL FINANCIALS ---
        # Revenue
        tourist_revenue = tourist_rental_days * params["tourist_rental_price_per_day"]
        friends_revenue = params["friends_rental_days_per_year"] * params["friends_rental_price_per_day"]
        total_rental_revenue = tourist_revenue + friends_revenue
        
        # Costs
        interest_paid = remaining_loan * current_interest_rate
        
        # Handle end of mortgage term
        principal_paid = annual_principal_payment if remaining_loan > annual_principal_payment else remaining_loan
        
        # Net Cash Flow for the year (what's left in your pocket)
        net_cash_flow = total_rental_revenue - interest_paid - principal_paid - current_fixed_costs
        cash_flows.append(net_cash_flow)

        # --- UPDATE STATE FOR NEXT YEAR ---
        remaining_loan -= principal_paid
        current_equity = current_property_value - remaining_loan
        
        # Store results for the year
        simulation_data.append([
            year, current_property_value, remaining_loan, current_equity, total_rental_revenue,
            current_interest_rate, interest_paid, principal_paid, current_fixed_costs,
            net_cash_flow
        ])

    # --- FINAL (TERMINAL) VALUE CALCULATION ---
    # At the end of the simulation, we "sell" the apartment to realize the final returns.
    selling_costs = current_property_value * params["selling_costs_pct"]
    proceeds_from_sale = current_property_value - selling_costs
    final_cash_inflow = proceeds_from_sale - remaining_loan

    # The final cash flow is the net cash flow of the last year plus the net proceeds from the sale.
    cash_flows[-1] += final_cash_inflow
    
    # --- CALCULATE RESULTS ---
    # Calculate the Internal Rate of Return (IRR) from the complete cash flow stream
    annualized_return = npf.irr(cash_flows)
    results_df = pd.DataFrame(simulation_data, columns=columns)
    
    return annualized_return, results_df

def find_breakeven_days(params):
    """
    Calculates the number of tourist rental days required to meet the target annual return.

    Args:
        params (dict): The simulation configuration parameters.

    Returns:
        int: The number of days required to meet the target return. Returns -1 if not achievable within 365 days.
    """
    print(f"\nSearching for the number of tourist rental days to achieve a {params['target_annual_return']:.1%} annualized return...")
    
    for days in range(0, 366):
        # We set a random seed to ensure the market conditions are the same for each iteration of this search
        np.random.seed(42)
        
        irr, _ = run_simulation(params, tourist_rental_days=days)
        if irr >= params["target_annual_return"]:
            return days
            
    return -1 # Return -1 if the target is not met even with 365 rental days


if __name__ == "__main__":
    # --- RUN ANALYSIS ---

    # Part 1: Run a simulation with an initial guess for rental days (e.g., 90 days)
    initial_guess_days = 90
    print("-" * 80)
    print(f"Running 10-Year Simulation with an assumption of {initial_guess_days} tourist rental days per year.")
    print("-" * 80)

    # Set a seed for reproducibility of the results
    np.random.seed(42)
    final_return, yearly_data = run_simulation(PARAMS, tourist_rental_days=initial_guess_days)

    # --- DISPLAY RESULTS ---
    pd.set_option('display.float_format', '{:,.2f}'.format)
    print(yearly_data.to_string(index=False))
    print("-" * 80)
    print(f"With {initial_guess_days} tourist rental days per year, the estimated annualized return (IRR) is: {final_return:.2%}")
    print("-" * 80)
    
    # Part 2: Find the number of days needed to reach the 5% target
    breakeven_days = find_breakeven_days(PARAMS)

    print("-" * 80)
    if breakeven_days != -1:
        print(f"✅ SUCCESS: To achieve your target of a {PARAMS['target_annual_return']:.1%} annualized return, you need to rent to tourists for approximately {breakeven_days} days per year.")
    else:
        print(f"❌ TARGET NOT MET: The simulation indicates that the {PARAMS['target_annual_return']:.1%} target return may not be achievable, even with 365 rental days per year under the current assumptions.")
    print("-" * 80)

