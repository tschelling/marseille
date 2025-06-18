import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import numpy_financial as npf

# --- FINANCIAL SIMULATION CORE ---
# This version of the simulation is fully deterministic.

def run_simulation(params, tourist_rental_days):
    """
    Runs a deterministic financial simulation for the apartment investment.
    """
    # --- INITIAL CALCULATIONS ---
    initial_down_payment = params["apartment_price"] - params["loan_amount"]
    buying_costs = params["apartment_price"] * params["buying_costs_pct"]
    total_initial_investment = initial_down_payment + buying_costs
    cash_flows = [-total_initial_investment]

    # --- SETUP DATAFRAME ---
    columns = [
        "Year", "Property Value", "Loan Balance", "Equity", "Rental Revenue",
        "Interest Rate", "Property Growth", "Interest Paid", "Principal Paid", 
        "Fixed Costs", "Net Cash Flow"
    ]
    simulation_data = []

    # --- INITIALIZE STATE ---
    remaining_loan = params["loan_amount"]
    current_property_value = params["apartment_price"]
    annual_principal_payment = params["loan_amount"] / params["mortgage_term_years"]
    
    # --- SIMULATION LOOP ---
    for year in range(1, params["simulation_years"] + 1):
        # Deterministic values: no random shocks
        current_interest_rate = params["base_mortgage_interest_rate"]
        current_property_growth = params["avg_property_value_growth"]
        
        current_property_value *= (1 + current_property_growth)
        current_fixed_costs = params["annual_fixed_costs"] * ((1 + params["annual_costs_inflation"]) ** year)

        # Revenue & Costs
        tourist_revenue = tourist_rental_days * params["tourist_rental_price_per_day"] # tourist_rental_days is from slider
        friends_revenue = params["friends_rental_days_per_year"] * params["friends_rental_price_per_day"]
        family_revenue = params["family_rental_days_per_year"] * params["family_rental_price_per_day"]
        total_rental_revenue = tourist_revenue + friends_revenue + family_revenue
        interest_paid = remaining_loan * current_interest_rate
        principal_paid = annual_principal_payment if remaining_loan > annual_principal_payment else remaining_loan
        net_cash_flow = total_rental_revenue - interest_paid - principal_paid - current_fixed_costs
        cash_flows.append(net_cash_flow)

        # Update state
        remaining_loan -= principal_paid
        current_equity = current_property_value - remaining_loan
        
        simulation_data.append([
            year, current_property_value, remaining_loan, current_equity, total_rental_revenue,
            current_interest_rate, current_property_growth, interest_paid, principal_paid, 
            current_fixed_costs, net_cash_flow
        ])

    # --- FINAL (TERMINAL) VALUE ---
    selling_costs = current_property_value * params["selling_costs_pct"]
    final_cash_inflow = (current_property_value - selling_costs) - remaining_loan
    cash_flows[-1] += final_cash_inflow
    
    # Handle cases where IRR can't be calculated (e.g., no profit)
    try:
        annualized_return = npf.irr(cash_flows)
    except:
        annualized_return = -1.0 # Return a value indicating loss
    
    results_df = pd.DataFrame(simulation_data, columns=columns)
    
    return annualized_return, results_df

def find_breakeven_days(params):
    """
    Calculates the breakeven days using the deterministic simulation.
    It uses the provided 'params' dictionary which should contain all up-to-date inputs.
    """
    for days in range(0, 366):
        irr, _ = run_simulation(params, tourist_rental_days=days)
        if irr >= params["target_annual_return"]:
            return days
    return -1

# --- DASH APPLICATION ---
# pip install dash dash-bootstrap-components pandas numpy numpy-financial
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
server = app.server

# --- Default Parameters ---
DEFAULT_PARAMS = {
    "simulation_years": 10, "apartment_price": 600000, "loan_amount": 300000,
    "mortgage_term_years": 25, "buying_costs_pct": 0.07, "selling_costs_pct": 0.05, # Keep friends_rental_days_per_year as it's not UI controlled
    "annual_fixed_costs": 6000, "tourist_rental_price_per_day": 300,
    "friends_rental_price_per_day": 80, "friends_rental_days_per_year": 15, # This is from a slider
    "family_rental_price_per_day": 50, "family_rental_days_per_year": 10, # Add new family defaults
    "avg_property_value_growth": 0.02, "annual_costs_inflation": 0.015, 
    "base_mortgage_interest_rate": 0.035,
    "target_annual_return": 0.05
}

# --- Reusable Components ---
def create_input_group(label, control_id, control):
    return dbc.Form([dbc.Label(label, html_for=control_id, className="fw-bold"), control])

# --- APP LAYOUT ---
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Marseille Wohnig Simulator", className="text-center my-4 text-primary"), width=12)),
    dbc.Row([
        # --- LEFT PANEL: CONTROLS ---
        dbc.Col([
            html.H4("Aanahme", className="mb-3"),
            dbc.Card(dbc.CardBody([
                create_input_group("Touri Vermietig Täg / Jahr", "tourist_days_slider", 
                    dcc.Slider(id="tourist_days_slider", min=0, max=365, step=1, value=90, marks={i: str(i) for i in range(0, 366, 30)})),
                html.Hr(),
                create_input_group("Fründe Vermietig Täg / Jahr", "friends_days_slider",
                    dcc.Slider(id="friends_days_slider", min=0, max=365, step=1, value=DEFAULT_PARAMS['friends_rental_days_per_year'], marks={i: str(i) for i in range(0, 366, 30)})),
                html.Hr(),
                create_input_group("Bsitzer Vermietig Täg / Jahr", "family_days_slider",
                    dcc.Slider(id="family_days_slider", min=0, max=365, step=1, value=DEFAULT_PARAMS['family_rental_days_per_year'], marks={i: str(i) for i in range(0, 366, 30)})),
                html.Hr(),
                create_input_group("Wohnigspriis (€)", "apartment_price_input", 
                    dbc.Input(id="apartment_price_input", type="number", value=DEFAULT_PARAMS['apartment_price'], step=10000)),
                create_input_group("Kredit (€)", "loan_amount_input", 
                    dbc.Input(id="loan_amount_input", type="number", value=DEFAULT_PARAMS['loan_amount'], step=10000)),
                create_input_group("Priissteigerig Wohnig (%/Jahr)", "property_growth_input", 
                    dbc.Input(id="property_growth_input", type="number", value=DEFAULT_PARAMS['avg_property_value_growth']*100, step=0.1)),
                create_input_group("Kreditzins (%/Jahr)", "interest_rate_input", 
                    dbc.Input(id="interest_rate_input", type="number", value=DEFAULT_PARAMS['base_mortgage_interest_rate']*100, step=0.1)),
                create_input_group("Turi Priis (€/Tag)", "tourist_price_input", 
                    dbc.Input(id="tourist_price_input", type="number", value=DEFAULT_PARAMS['tourist_rental_price_per_day'], step=5)),
                create_input_group("Fründe Priis (€/Tag)", "friends_price_input", 
                    dbc.Input(id="friends_price_input", type="number", value=DEFAULT_PARAMS['friends_rental_price_per_day'], step=5)),
                create_input_group("Bsitzer Priis (€/Tag)", "family_price_input", 
                    dbc.Input(id="family_price_input", type="number", value=DEFAULT_PARAMS['family_rental_price_per_day'], step=5)),
                create_input_group("Jährlichi Fixköste(€)", "fixed_costs_input", 
                    dbc.Input(id="fixed_costs_input", type="number", value=DEFAULT_PARAMS['annual_fixed_costs'], step=100)),
            ]))
        ], md=4),
        
        # --- RIGHT PANEL: RESULTS ---
        dbc.Col([
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H6("Rendite (IRR)", className="card-title"),
                    html.H2(id='irr_output', className="text-primary")
                ], className="text-center")), md=6),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H6("Täg zum 5% Rendite erreiche", className="card-title"),
                    html.H2(id='breakeven_output', className="text-success")
                ], className="text-center")), md=6),
            ]),
            dbc.Row(dbc.Col(dcc.Graph(id='investment_chart'), className="mt-4")),
        ], md=8),
    ])
    , dbc.Row(dbc.Col(dcc.Graph(id='costs_chart'), className="mt-4")),
], fluid=True, className="dbc")

# --- CALLBACK ---
@app.callback(
    [Output('irr_output', 'children'),
     Output('breakeven_output', 'children'),
     Output('investment_chart', 'figure'),
     Output('costs_chart', 'figure')], # Moved this Output into the list
    # The callback now triggers when any input value changes)
    [Input('tourist_days_slider', 'value'),
     Input('friends_days_slider', 'value'),
     Input('family_days_slider', 'value'),
     Input('apartment_price_input', 'value'),
     Input('loan_amount_input', 'value'),
     Input('property_growth_input', 'value'),
     Input('interest_rate_input', 'value'),
     Input('tourist_price_input', 'value'),
     Input('friends_price_input', 'value'),
     Input('family_price_input', 'value'),
     Input('fixed_costs_input', 'value')]
)
def update_dashboard(tourist_days, friends_days, family_days, apt_price, loan_amt, prop_growth, int_rate, tourist_price, friends_price, family_price, fixed_costs):
    # --- UPDATE PARAMS ---
    params_for_run = DEFAULT_PARAMS.copy()

    # Update params_for_run with values from inputs, only if they are not None.
    # This prevents overwriting defaults with None if an input field is cleared.
    if apt_price is not None:
        params_for_run['apartment_price'] = apt_price
    if loan_amt is not None:
        params_for_run['loan_amount'] = loan_amt
    if prop_growth is not None:
        params_for_run['avg_property_value_growth'] = prop_growth / 100.0
    if int_rate is not None:
        params_for_run['base_mortgage_interest_rate'] = int_rate / 100.0
    if tourist_price is not None:
        params_for_run['tourist_rental_price_per_day'] = tourist_price
    if friends_price is not None:
        params_for_run['friends_rental_price_per_day'] = friends_price
    if fixed_costs is not None:
        params_for_run['annual_fixed_costs'] = fixed_costs
    if friends_days is not None: 
        params_for_run['friends_rental_days_per_year'] = friends_days
    if family_days is not None:
        params_for_run['family_rental_days_per_year'] = family_days
    if family_price is not None:
        params_for_run['family_rental_price_per_day'] = family_price
    
    # --- RUN SIMULATIONS ---
    # Ensure tourist_days is an int (slider usually ensures this, but a fallback is safe)
    sim_tourist_days = tourist_days if tourist_days is not None else 0
    irr, df = run_simulation(params_for_run, sim_tourist_days)

    # The breakeven calculation now correctly uses the same updated parameters.
    breakeven_days = find_breakeven_days(params_for_run)
    
    # --- CREATE OUTPUTS ---
    irr_text = f"{irr:.2%}"
    breakeven_text = f"{breakeven_days} days" if breakeven_days != -1 else "N/A"
    
    # --- Main Investment Chart ---
    fig_main = go.Figure()
    fig_main.add_trace(go.Scatter(x=df['Year'], y=df['Property Value'], mode='lines', name='Wohnigspriis', line=dict(color='royalblue', width=3), fill='tozeroy'))
    fig_main.add_trace(go.Scatter(x=df['Year'], y=df['Equity'], mode='lines', name='Eigekapital', line=dict(color='seagreen', width=3)))
    fig_main.add_trace(go.Bar(x=df['Year'], y=df['Net Cash Flow'], name='Stutz wo usegaht', yaxis='y2', marker_color='rgba(255, 99, 71, 0.6)'))
    fig_main.update_layout(title="<b>Projektione</b>", yaxis_title="Euros (€)",
        yaxis=dict(tickformat=",.0f"), yaxis2=dict(title="", overlaying='y', side='right', showgrid=False, tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

    # --- Costs Breakdown Chart ---
    fig_costs = go.Figure()
    fig_costs.add_trace(go.Bar(x=df['Year'], y=df['Interest Paid'], name='Zinszahlige', marker_color='#636EFA'))
    fig_costs.add_trace(go.Bar(x=df['Year'], y=df['Principal Paid'], name='Kreditrückzahlige', marker_color='#EF553B'))
    fig_costs.add_trace(go.Bar(x=df['Year'], y=df['Fixed Costs'], name='Fixköste', marker_color='#00CC96'))
    fig_costs.update_layout(
        title="<b>Jährlichi Köste</b>",
        xaxis_title="Jahr",
        yaxis_title="Euros (€)",
        yaxis=dict(tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode='stack'
    )
    
    return irr_text, breakeven_text, fig_main, fig_costs




if __name__ == '__main__':
    # To run the app, execute this script from your terminal
    app.run(debug=True)
