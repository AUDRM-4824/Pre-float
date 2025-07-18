import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time

def calculate_carbon_grades(rougher_air, jameson_air, luproset, feed_carbon):
    """Calculate concentrate and tailings carbon grades based on rougher air, jameson air and luproset"""
    
    # Base concentrate carbon grade
    base_conc_grade = 40.0  # Base concentrate grade
    
    # Rougher air rate effect: higher air rate DECREASES grade (linear relationship)
    rougher_air_grade_effect = -rougher_air * 0.012  # Decreases grade as air rate increases
    
    # Jameson air rate effect: same relationship as rougher air but half the effect
    jameson_air_grade_effect = -jameson_air * 0.006  # Half the effect of rougher air
    
    # Luproset effect: higher luproset INCREASES grade by depressing gangue
    luproset_grade_effect = luproset * 0.08
    
    # Calculate concentrate grade
    concentrate_carbon = base_conc_grade + rougher_air_grade_effect + jameson_air_grade_effect + luproset_grade_effect
    concentrate_carbon = max(20.0, min(60.0, concentrate_carbon))  # Max 60% as specified
    
    # Tailings carbon calculation
    # Higher luproset = higher tailings carbon (carbon depressed, stays in tailings)
    # Higher air rate = lower tailings carbon (more carbon floated)
    base_tail_grade = feed_carbon * 0.5  # Base case
    
    # Luproset INCREASES tailings carbon (depresses carbon)
    luproset_tail_effect = luproset * 0.07
    
    # Higher rougher air rate DECREASES tailings carbon (more recovery)
    rougher_air_tail_effect = -rougher_air * 0.005
    
    # Higher jameson air rate DECREASES tailings carbon (more recovery) - half effect
    jameson_air_tail_effect = -jameson_air * 0.0025
    
    tailings_carbon = base_tail_grade + luproset_tail_effect + rougher_air_tail_effect + jameson_air_tail_effect
    tailings_carbon = max(0.2, min(feed_carbon * 1, tailings_carbon))
    
    return concentrate_carbon, tailings_carbon

def calculate_mass_balance(feed_carbon, concentrate_carbon, tailings_carbon, feed_tonnage=260):
    """Calculate mass balance for reverse flotation"""
    try:
        # Mass balance: Feed = Concentrate + Tailings
        concentrate_mass = feed_tonnage * (feed_carbon - tailings_carbon) / (concentrate_carbon - tailings_carbon)
        tailings_mass = feed_tonnage - concentrate_mass
        
        # Calculate carbon recovery to concentrate
        carbon_recovery = (concentrate_mass * concentrate_carbon) / (feed_tonnage * feed_carbon) * 100
        
        # Ensure physical constraints
        concentrate_mass = max(0, min(feed_tonnage * 0.5, concentrate_mass))  # Max 50% to concentrate
        tailings_mass = feed_tonnage - concentrate_mass
        carbon_recovery = max(0, min(100, carbon_recovery))
        
        return concentrate_mass, tailings_mass, carbon_recovery
    except:
        return 10, 90, 50  # Default values if calculation fails

def calculate_zn_loss(carbon_recovery):
    """Calculate Zn loss based on carbon recovery (0.5% to 4% range)"""
    # Linear relationship: as carbon recovery increases, Zn loss increases
    # Recovery range: 10-55%, Zn loss range: 0.5-4%
    min_recovery, max_recovery = 10, 55
    min_zn_loss, max_zn_loss = 0.1, 4.0
    
    # Normalize recovery to 0-1 range
    normalized_recovery = (carbon_recovery - min_recovery) / (max_recovery - min_recovery)
    normalized_recovery = max(0, min(1, normalized_recovery))  # Clamp to 0-1
    
    # Calculate Zn loss
    zn_loss = min_zn_loss + (normalized_recovery * (max_zn_loss - min_zn_loss))
    
    return zn_loss

def calculate_performance(rougher_air, jameson_air, luproset, feed_carbon):
    """Calculate flotation performance from rougher air, jameson air and luproset"""
    
    # Calculate concentrate and tailings carbon grades
    concentrate_carbon, tailings_carbon = calculate_carbon_grades(rougher_air, jameson_air, luproset, feed_carbon)
    
    # Calculate mass balance
    conc_mass, tail_mass, carbon_recovery = calculate_mass_balance(
        feed_carbon, concentrate_carbon, tailings_carbon
    )
    
    # Calculate overall recovery based on air rates and luproset
    # Higher rougher air rate = HIGHER recovery (linear relationship)
    rougher_air_recovery_effect = rougher_air * 0.045  # Linear increase with air rate
    
    # Higher jameson air rate = HIGHER recovery (linear relationship) - half effect
    jameson_air_recovery_effect = jameson_air * 0.0225  # Half the effect of rougher air
    
    # Higher luproset REDUCES recovery (carbon depressed to tailings)
    luproset_recovery_effect = -luproset * 0.015  # Reduces recovery
    
    base_recovery = 0.0  # Base recovery
    total_recovery = base_recovery + rougher_air_recovery_effect + jameson_air_recovery_effect + luproset_recovery_effect
    total_recovery = max(10, min(55, total_recovery))
    
    # Calculate Zn loss
    zn_loss = calculate_zn_loss(total_recovery)
    
    return total_recovery, concentrate_carbon, tailings_carbon, conc_mass, tail_mass, carbon_recovery, zn_loss

# Streamlit App
st.set_page_config(
    page_title="Carbon Reverse Flotation Simulator",
    page_icon="⚫",
    layout="wide"
)

st.title("⚫ Pre Flotation Simulator")
st.markdown("Parameters - Rougher Air, Jameson Air & Luproset")

# Sidebar controls - now with 4 parameters
st.sidebar.header("Process Parameters")

rougher_air = st.sidebar.slider(
    "Rougher Air (m3/hr)",
    min_value=0, max_value=1000, value=0, step=50,
    help="Rougher air rate - HIGHER increases recovery but decreases grade"
)

jameson_air = st.sidebar.slider(
    "Jameson Air (m3/hr)",
    min_value=0, max_value=600, value=0, step=25,
    help="Jameson air rate - Same effect as rougher air but half the magnitude"
)

luproset = st.sidebar.slider(
    "Luproset Dosage (g/t)",
    min_value=0, max_value=100, value=80, step=5,
    help="Carbon depressant - HIGHER reduces recovery but increases grade"
)

feed_carbon = st.sidebar.slider(
    "Feed Carbon (%)",
    min_value=3.0, max_value=6.0, value=4.5, step=0.1,
    help="Carbon content in feed stream"
)

# Calculate performance
recovery, concentrate_carbon, tailings_carbon, conc_mass, tail_mass, mass_balance_recovery, zn_loss = calculate_performance(
    rougher_air, jameson_air, luproset, feed_carbon
)

# Main dashboard
st.subheader("Process Performance")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Carbon Recovery", 
        f"{recovery:.1f}%"
    )

with col2:
    st.metric(
        "Concentrate Carbon", 
        f"{concentrate_carbon:.1f}%"
    )

with col3:
    # Custom delta logic for tailings carbon - red if outside 2.8-3.0% range
    if 2.8 <= tailings_carbon <= 3.0:
        tail_delta = None  # No arrow if in target range
        tail_delta_color = "normal"
    else:
        # Always show positive delta value but make it red
        tail_delta = f"{abs(tailings_carbon - 2.9):.2f}%"
        tail_delta_color = "inverse"  # Red for any deviation from target range
    
    st.metric(
        "Tailings Carbon", 
        f"{tailings_carbon:.2f}%",
        delta=tail_delta,
        delta_color=tail_delta_color
    )

with col4:
    st.metric(
        "Concentrate Mass", 
        f"{conc_mass:.1f}t"
    )

with col5:
    st.metric(
        "Zn Loss", 
        f"{zn_loss:.2f}%",
        delta=f"{zn_loss - 1.5:.2f}%" if zn_loss != 1.5 else None,
        delta_color="inverse"
    )

# Stream summary
st.subheader("Stream Summary (Base: 260t Feed)")
col1, col2, col3 = st.columns(3)

with col1:
    st.info(f"""
    **Feed Stream**
    - Mass: 260.0 t
    - Carbon: {feed_carbon:.1f}%
    - Total Carbon: {feed_carbon * 260 / 100:.1f} t
    """)

with col2:
    st.success(f"""
    **Concentrate Stream**
    - Mass: {conc_mass:.1f} t
    - Carbon: {concentrate_carbon:.1f}%
    - Total Carbon: {conc_mass * concentrate_carbon / 100:.1f} t
    """)

with col3:
    st.warning(f"""
    **Tailings Stream**
    - Mass: {tail_mass:.1f} t
    - Carbon: {tailings_carbon:.2f}%
    - Total Carbon: {tail_mass * tailings_carbon / 100:.1f} t
    """)

# Performance visualization
col1, col2 = st.columns(2)

with col1:
    # Grade-Recovery plot
    fig1 = go.Figure()
    
    # Add current operating point
    fig1.add_scatter(
        x=[recovery], y=[concentrate_carbon],
        mode='markers',
        marker=dict(size=15, color='black', symbol='star'),
        name='Current Operation',
        text=[f'Rougher: {rougher_air}, Jameson: {jameson_air}, Luproset: {luproset}'],
        textposition="top center"
    )
    
    # Add target zone
    fig1.add_shape(
        type="rect",
        x0=50, y0=40, x1=70, y1=55,
        fillcolor="lightgreen", opacity=0.3,
        line=dict(color="green", width=2)
    )
    
    fig1.add_annotation(
        x=60, y=47.5,
        text="Target Zone",
        showarrow=False,
        font=dict(color="green", size=12)
    )
    
    fig1.update_layout(
        title="Carbon Grade vs Recovery",
        xaxis_title="Carbon Recovery (%)",
        yaxis_title="Concentrate Carbon Grade (%)",
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    # Parameter effects plot - comparing rougher and jameson air
    fig2 = go.Figure()
    
    # Air rate effect comparison
    air_range = np.linspace(100, 1000, 20)
    recovery_rougher = [calculate_performance(a, jameson_air, luproset, feed_carbon)[0] for a in air_range]
    grade_rougher = [calculate_performance(a, jameson_air, luproset, feed_carbon)[1] for a in air_range]
    zn_loss_rougher = [calculate_performance(a, jameson_air, luproset, feed_carbon)[6] for a in air_range]
    
    # Scale jameson range to similar values for comparison
    jameson_range = np.linspace(50, 500, 20)
    recovery_jameson = [calculate_performance(rougher_air, j, luproset, feed_carbon)[0] for j in jameson_range]
    grade_jameson = [calculate_performance(rougher_air, j, luproset, feed_carbon)[1] for j in jameson_range]
    zn_loss_jameson = [calculate_performance(rougher_air, j, luproset, feed_carbon)[6] for j in jameson_range]
    
    fig2.add_trace(go.Scatter(
        x=air_range, y=recovery_rougher,
        mode='lines', name='Recovery vs Rougher Air',
        line=dict(color='blue', dash='solid')
    ))
    
    fig2.add_trace(go.Scatter(
        x=jameson_range, y=recovery_jameson,
        mode='lines', name='Recovery vs Jameson Air',
        line=dict(color='lightblue', dash='dash')
    ))
    
    fig2.add_trace(go.Scatter(
        x=air_range, y=grade_rougher,
        mode='lines', name='Grade vs Rougher Air',
        line=dict(color='red', dash='solid'), yaxis='y2'
    ))
    
    fig2.add_trace(go.Scatter(
        x=jameson_range, y=grade_jameson,
        mode='lines', name='Grade vs Jameson Air',
        line=dict(color='pink', dash='dash'), yaxis='y2'
    ))
    
    # Add Zn loss curves
    fig2.add_trace(go.Scatter(
        x=air_range, y=zn_loss_rougher,
        mode='lines', name='Zn Loss vs Rougher Air',
        line=dict(color='orange', dash='solid'), yaxis='y3'
    ))
    
    fig2.add_trace(go.Scatter(
        x=jameson_range, y=zn_loss_jameson,
        mode='lines', name='Zn Loss vs Jameson Air',
        line=dict(color='gold', dash='dash'), yaxis='y3'
    ))
    
    # Add current points
    fig2.add_scatter(
        x=[rougher_air], y=[recovery],
        mode='markers', marker=dict(size=12, color='blue'),
        name='Current Recovery (Rougher)'
    )
    
    fig2.add_scatter(
        x=[jameson_air], y=[recovery],
        mode='markers', marker=dict(size=10, color='lightblue', symbol='square'),
        name='Current Recovery (Jameson)'
    )
    
    fig2.update_layout(
        title="Air Rate Effects Comparison",
        xaxis_title="Air Rate (m3/hr)",
        yaxis=dict(title="Recovery (%)", side="left", color="blue"),
        yaxis2=dict(title="Grade (%)", side="right", overlaying="y", color="red"),
        yaxis3=dict(title="Zn Loss (%)", side="right", overlaying="y", position=0.95, color="orange"),
        height=400,
        legend=dict(x=0.02, y=0.98)
    )
    
    st.plotly_chart(fig2, use_container_width=True)

# Real-time trends
if 'history' not in st.session_state:
    st.session_state.history = []

# Add to history when parameters change
current_params = (rougher_air, jameson_air, luproset, feed_carbon)
if 'last_params' not in st.session_state or st.session_state.last_params != current_params:
    st.session_state.history.append({
        'time': len(st.session_state.history),
        'rougher_air': rougher_air,
        'jameson_air': jameson_air,
        'luproset': luproset,
        'recovery': recovery,
        'conc_grade': concentrate_carbon,
        'tail_grade': tailings_carbon,
        'conc_mass': conc_mass,
        'zn_loss': zn_loss
    })
    st.session_state.last_params = current_params

# Keep only last 30 points
if len(st.session_state.history) > 30:
    st.session_state.history = st.session_state.history[-30:]

# Trends plot
if len(st.session_state.history) > 1:
    df_history = pd.DataFrame(st.session_state.history)
    
    st.subheader("Process Trends")
    
    fig3 = make_subplots(
        rows=3, cols=2,
        subplot_titles=('Recovery & Grade Trends', 'Air Rate Settings', 'Mass Distribution & Luproset', 'Tailings Carbon', 'Zn Loss Trend', 'Recovery vs Zn Loss'),
        specs=[[{"secondary_y": True}, {"secondary_y": True}],
               [{"secondary_y": True}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Recovery and grade trends
    fig3.add_trace(
        go.Scatter(x=df_history['time'], y=df_history['recovery'], 
                  name='Recovery', line=dict(color='blue')),
        row=1, col=1
    )
    fig3.add_trace(
        go.Scatter(x=df_history['time'], y=df_history['conc_grade'], 
                  name='Conc Grade', line=dict(color='red')),
        row=1, col=1, secondary_y=True
    )
    
    # Air rate settings
    fig3.add_trace(
        go.Scatter(x=df_history['time'], y=df_history['rougher_air'], 
                  name='Rougher Air', line=dict(color='green')),
        row=1, col=2
    )
    fig3.add_trace(
        go.Scatter(x=df_history['time'], y=df_history['jameson_air'], 
                  name='Jameson Air', line=dict(color='lightgreen')),
        row=1, col=2, secondary_y=True
    )
    
    # Mass distribution and luproset
    fig3.add_trace(
        go.Scatter(x=df_history['time'], y=df_history['conc_mass'], 
                  name='Conc Mass', line=dict(color='black')),
        row=2, col=1
    )
    fig3.add_trace(
        go.Scatter(x=df_history['time'], y=df_history['luproset'], 
                  name='Luproset', line=dict(color='orange')),
        row=2, col=1, secondary_y=True
    )
    
    # Tailings grade
    fig3.add_trace(
        go.Scatter(x=df_history['time'], y=df_history['tail_grade'], 
                  name='Tail Grade', line=dict(color='brown')),
        row=2, col=2
    )
    
    # Zn loss trend
    fig3.add_trace(
        go.Scatter(x=df_history['time'], y=df_history['zn_loss'], 
                  name='Zn Loss', line=dict(color='purple')),
        row=3, col=1
    )
    
    # Recovery vs Zn Loss correlation
    fig3.add_trace(
        go.Scatter(x=df_history['recovery'], y=df_history['zn_loss'], 
                  mode='markers', name='Recovery vs Zn Loss', 
                  marker=dict(color='red', size=6)),
        row=3, col=2
    )
    
    fig3.update_layout(height=800, title_text="Historical Performance")
    st.plotly_chart(fig3, use_container_width=True)

# Operating guidance
st.subheader("Operating Guidance")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Parameter Effects:**")
    st.markdown("- **Higher Rougher Air** = Higher recovery, Lower grade, Higher Zn loss")
    st.markdown("- **Higher Jameson Air** = Higher recovery, Lower grade, Higher Zn loss")
    st.markdown("- **Higher Luproset** = Lower recovery, Higher grade, Lower Zn loss")
    st.markdown("- **Target Recovery**: 20-45%")
    st.markdown("- **Target Concentrate Grade**: 30-45%")
    st.markdown("- **Target Zn Loss**: <2.5%")
    

with col2:
    st.markdown("**Optimization Tips:**")
    if recovery < 30:
        st.markdown("🔧 **To increase recovery:**")
        st.markdown("- Increase rougher air rate")
        st.markdown("- Increase jameson air rate")
        st.markdown("- Reduce luproset dosage")
    
    if concentrate_carbon < 30:
        st.markdown("🔧 **To increase grade:**")
        st.markdown("- Reduce rougher air rate")
        st.markdown("- Reduce jameson air rate")
        st.markdown("- Increase luproset dosage")
    
    if tailings_carbon > 3.5:
        st.markdown("⚠️ **High tailings carbon - check:**")
        st.markdown("- Reduce luproset (less carbon depressed)")
        st.markdown("- Increase air rates (more recovery)")
    
    if zn_loss > 2.5:
        st.markdown("⚠️ **High Zn loss - check:**")
        st.markdown("- Reduce air rates (lower recovery)")
        st.markdown("- Increase luproset (reduce recovery)")
        st.markdown("- Balance recovery vs Zn retention")

# Reset button
if st.button("Reset Trends", type="secondary"):
    st.session_state.history = []
    st.rerun()