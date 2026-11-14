
import streamlit as st
import pandas as pd

from calculations import BendInputs, calculate_v_bending


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="V-Bend Springback Calculator",
    page_icon="📐",
    layout="wide"
)


# ==========================================
# MATERIAL DATABASE
# ==========================================

MATERIALS = {
    "Mild Steel": (210.0, 250.0, 410.0),
    "Stainless Steel 304": (193.0, 215.0, 505.0),
    "Aluminium 5052-H32": (70.3, 193.0, 228.0),
    "Aluminium 6061-T6": (68.9, 276.0, 310.0),
    "Custom Material": (210.0, 250.0, 410.0)
}


# ==========================================
# SESSION STATE
# ==========================================

if "result" not in st.session_state:
    st.session_state.result = None

if "error" not in st.session_state:
    st.session_state.error = None


# ==========================================
# WEBSITE TITLE
# ==========================================

st.title("V-Bend Springback Calculator")

st.write(
    "Calculate sheet metal springback and estimated "
    "bending force during V-bending."
)


# ==========================================
# SIDEBAR INPUTS
# ==========================================

st.sidebar.header("Process Parameters")

with st.sidebar.form("calculator_form"):

    st.subheader("Material Properties")

    material_name = st.selectbox(
        "Material",
        list(MATERIALS.keys())
    )

    E, sy, uts = MATERIALS[material_name]

    youngs_modulus = st.number_input(
        "Young's Modulus (GPa)",
        min_value=0.1,
        value=float(E)
    )

    yield_strength = st.number_input(
        "Yield Strength (MPa)",
        min_value=0.1,
        value=float(sy)
    )

    tensile_strength = st.number_input(
        "Tensile Strength (MPa)",
        min_value=0.1,
        value=float(uts)
    )

    st.subheader("Sheet Parameters")

    thickness = st.number_input(
        "Sheet Thickness (mm)",
        min_value=0.1,
        value=2.0
    )

    width = st.number_input(
        "Sheet Width (mm)",
        min_value=0.1,
        value=50.0
    )

    st.subheader("Bending Parameters")

    target_angle = st.number_input(
        "Target Final Included Angle (°)",
        min_value=0.1,
        max_value=179.9,
        value=90.0
    )

    applied_angle = st.number_input(
        "Applied Loaded Included Angle (°)",
        min_value=0.1,
        max_value=179.9,
        value=85.0
    )

    punch_radius = st.number_input(
        "Punch Radius (mm)",
        min_value=0.1,
        value=2.0
    )

    die_opening = st.number_input(
        "V-Die Opening (mm)",
        min_value=0.1,
        value=16.0
    )

    friction = st.number_input(
        "Friction Coefficient",
        min_value=0.0,
        max_value=1.0,
        value=0.1
    )

    use_force = st.checkbox(
        "Enter Applied Force"
    )

    applied_force = None

    if use_force:
        applied_force = st.number_input(
            "Applied Force (N)",
            min_value=0.0,
            value=10000.0
        )

    calculate = st.form_submit_button(
        "Calculate Springback",
        width="stretch"
    )


# ==========================================
# CALCULATION
# ==========================================

if calculate:

    try:

        inputs = BendInputs(
            youngs_modulus_gpa=youngs_modulus,
            yield_strength_mpa=yield_strength,
            tensile_strength_mpa=tensile_strength,
            thickness_mm=thickness,
            width_mm=width,
            target_final_angle_deg=target_angle,
            applied_loaded_angle_deg=applied_angle,
            punch_radius_mm=punch_radius,
            die_opening_mm=die_opening,
            friction_coefficient=friction,
            applied_force_n=applied_force
        )

        st.session_state.result = calculate_v_bending(inputs)
        st.session_state.error = None

    except (ValueError, TypeError) as error:

        st.session_state.result = None
        st.session_state.error = str(error)


# ==========================================
# DISPLAY ERROR
# ==========================================

if st.session_state.error:
    st.error(st.session_state.error)


# ==========================================
# PREDICTED RESULTS
# ==========================================

result = st.session_state.result

if result is not None:

    st.divider()

    st.header("Predicted Results")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Springback Angle",
        f'{result["springback_angle_deg"]:.3f}°'
    )

    c2.metric(
        "Final Included Angle",
        f'{result["final_included_angle_deg"]:.3f}°'
    )

    c3.metric(
        "Angle Deviation",
        f'{result["angle_deviation_deg"]:+.3f}°'
    )

    c4.metric(
        "Required Overbend",
        f'{result["overbend_angle_deg"]:.3f}°'
    )

    c5, c6, c7, c8 = st.columns(4)

    c5.metric(
        "Springback Ratio",
        f'{result["springback_ratio_angle"]:.5f}'
    )

    c6.metric(
        "Final Inside Radius",
        f'{result["final_inside_radius_mm"]:.3f} mm'
    )

    c7.metric(
        "Maximum Bending Stress",
        f'{result["maximum_bending_stress_mpa"]:.1f} MPa'
    )

    c8.metric(
        "Maximum Bending Strain",
        f'{result["maximum_bending_strain"]:.5f}'
    )

    st.divider()

    # ======================================
    # BENDING FORCE
    # ======================================

    st.subheader("Bending Force")

    st.metric(
        "Estimated V-Bending Force",
        f'{result["estimated_bending_force_n"] / 1000:.3f} kN'
    )

    if result["force_comparison"] is not None:

        st.write(
            "Applied Force: "
            f'{result["force_comparison"]["applied_force_n"] / 1000:.3f} kN'
        )

    st.divider()

    # ======================================
    # CALCULATION REPORT
    # ======================================

    st.subheader("Calculation Report")

    report = pd.DataFrame(
        [
            ["Springback Angle",
             result["springback_angle_deg"], "degree"],

            ["Final Included Angle",
             result["final_included_angle_deg"], "degree"],

            ["Angle Deviation",
             result["angle_deviation_deg"], "degree"],

            ["Required Overbend",
             result["overbend_angle_deg"], "degree"],

            ["Springback Ratio",
             result["springback_ratio_angle"], "-"],

            ["Final Inside Radius",
             result["final_inside_radius_mm"], "mm"],

            ["Maximum Bending Stress",
             result["maximum_bending_stress_mpa"], "MPa"],

            ["Maximum Bending Strain",
             result["maximum_bending_strain"], "-"],

            ["Estimated Bending Force",
             result["estimated_bending_force_n"], "N"]
        ],
        columns=["Parameter", "Value", "Unit"]
    )

    st.dataframe(
        report,
        width="stretch",
        hide_index=True
    )

    st.download_button(
        "Download CSV Report",
        data=report.to_csv(index=False).encode("utf-8"),
        file_name="v_bending_springback_report.csv",
        mime="text/csv",
        width="stretch"
    )


else:

    st.info(
        "Enter the process parameters in the sidebar "
        "and click Calculate Springback."
    )


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "Educational engineering tool. Validate predictions "
    "against measured bends and material certificates. "
    "Do not use as the sole basis for production or safety decisions."
)

st.caption(
    "Reference: Zhang et al. (2007), "
    "An analytical model for predicting sheet springback after V-bending."
)

st.markdown(
    "[Read the reference paper](https://doi.org/10.1631/jzus.2007.A0237)"
)
