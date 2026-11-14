"""Engineering calculations for the V-bending springback calculator.

Springback:
    Gardiner elastic-perfectly-plastic pure-bending approximation.
    This is a screening model, not a full V-die/contact model.

Bending force:
    Conventional V-bending estimate F = 1.33 * UTS * width * thickness^2 / die_opening.
    Units: MPa=N/mm^2, dimensions=mm, result=N.
"""

from dataclasses import dataclass
import math


@dataclass
class BendInputs:
    youngs_modulus_gpa: float
    yield_strength_mpa: float
    tensile_strength_mpa: float
    thickness_mm: float
    width_mm: float
    target_final_angle_deg: float
    applied_loaded_angle_deg: float
    punch_radius_mm: float
    die_opening_mm: float
    friction_coefficient: float | None = None
    applied_force_n: float | None = None


def validate_inputs(p: BendInputs) -> list[str]:
    errors = []
    positive_fields = {
        "Young's modulus": p.youngs_modulus_gpa,
        "Yield strength": p.yield_strength_mpa,
        "Tensile strength": p.tensile_strength_mpa,
        "Thickness": p.thickness_mm,
        "Width": p.width_mm,
        "Punch radius": p.punch_radius_mm,
        "V-die opening": p.die_opening_mm,
    }
    for name, value in positive_fields.items():
        if value <= 0:
            errors.append(f"{name} must be greater than zero.")

    if not (0 < p.target_final_angle_deg < 180):
        errors.append("Target included angle must be between 0° and 180°.")
    if not (0 < p.applied_loaded_angle_deg < 180):
        errors.append("Applied included angle must be between 0° and 180°.")
    if p.friction_coefficient is not None and not (0 <= p.friction_coefficient <= 1):
        errors.append("Friction coefficient must be between 0 and 1.")
    if p.applied_force_n is not None and p.applied_force_n < 0:
        errors.append("Applied force cannot be negative.")
    return errors


def calculate_v_bending(p: BendInputs) -> dict:
    """Return calculated values and model warnings.

    Angle convention:
      - Included angle between the two sheet legs.
      - A smaller included angle means a tighter bend.
      - Springback increases the included angle after unloading.

    Radius assumption:
      - The punch radius is used as the loaded inside bend radius.
      - This is not generally exact in air bending; actual radius depends on
        tooling, material, and process.
    """
    errors = validate_inputs(p)
    if errors:
        raise ValueError(" ".join(errors))

    E_mpa = p.youngs_modulus_gpa * 1000.0
    t = p.thickness_mm
    Ri = p.punch_radius_mm
    sy = p.yield_strength_mpa

    # Gardiner parameter and radius ratio: Ri/Rf = 1 - 3x + 4x^3
    x = (Ri * sy) / (E_mpa * t)
    radius_ratio = 1.0 - 3.0 * x + 4.0 * (x ** 3)

    warnings = [
        "Gardiner model assumes pure bending, elastic-perfectly-plastic material "
        "behaviour and idealised unloading. It does not explicitly model V-die "
        "contact pressure, friction, transverse stress, anisotropy or hardening.",
        "Punch radius is assumed to equal the loaded inside bend radius. This "
        "assumption can be poor in air bending.",
        "The friction input is recorded but is not used by the Gardiner equation.",
        "Maximum bending stress is represented by the yield strength under the "
        "ideal elastic-perfectly-plastic assumption; it is not a detailed stress-field solution.",
    ]

    if x >= 0.5 or radius_ratio <= 0:
        raise ValueError(
            "The selected inputs fall outside the yielding branch of this "
            "Gardiner approximation (x must be below 0.5). A reliable permanent "
            "bend prediction cannot be produced by this model."
        )

    Rf = Ri / radius_ratio

    # Neutral-fibre length conservation; mid-thickness neutral-axis approximation.
    angle_ratio = (Ri + t / 2.0) / (Rf + t / 2.0)

    beta_loaded = 180.0 - p.applied_loaded_angle_deg
    beta_final = beta_loaded * angle_ratio
    final_included_angle = 180.0 - beta_final

    springback_angle = final_included_angle - p.applied_loaded_angle_deg
    angle_deviation = final_included_angle - p.target_final_angle_deg

    target_beta = 180.0 - p.target_final_angle_deg
    required_loaded_beta = target_beta / angle_ratio
    required_loaded_included_angle = 180.0 - required_loaded_beta
    overbend_angle = p.target_final_angle_deg - required_loaded_included_angle

    # Approximate outer-fibre logarithmic bending strain, neutral axis at mid-thickness.
    max_bending_strain = math.log((Ri + t) / (Ri + t / 2.0))

    # Conventional V-bending force estimate, based on ultimate tensile strength.
    estimated_force_n = (
        1.33 * p.tensile_strength_mpa * p.width_mm * (t ** 2) / p.die_opening_mm
    )

    force_comparison = None
    if p.applied_force_n is not None:
        force_comparison = {
            "applied_force_n": p.applied_force_n,
            "estimated_force_n": estimated_force_n,
            "ratio_applied_to_estimated": (
                p.applied_force_n / estimated_force_n if estimated_force_n else None
            ),
        }

    if Ri / t < 5:
        warnings.append(
            "Punch-radius/thickness ratio is below 5. Zhang et al. report that "
            "contact pressure and transverse stress can have a significant effect "
            "in this range; the Gardiner pure-bending estimate may underpredict "
            "or otherwise misrepresent actual V-bending springback."
        )

    if p.die_opening_mm / t < 4 or p.die_opening_mm / t > 16:
        warnings.append(
            "The V-die opening/thickness ratio is outside the common 4t–16t "
            "range used by the selected simplified force estimate. Treat the "
            "estimated force as a rough screening value."
        )

    if p.tensile_strength_mpa < p.yield_strength_mpa:
        warnings.append(
            "Tensile strength is lower than yield strength. Check the material data."
        )

    return {
        "gardiner_parameter_x": x,
        "springback_ratio_radius": radius_ratio,
        "springback_ratio_angle": angle_ratio,
        "loaded_inside_radius_mm": Ri,
        "final_inside_radius_mm": Rf,
        "springback_angle_deg": springback_angle,
        "final_included_angle_deg": final_included_angle,
        "angle_deviation_deg": angle_deviation,
        "required_loaded_included_angle_deg": required_loaded_included_angle,
        "overbend_angle_deg": overbend_angle,
        "maximum_bending_stress_mpa": sy,
        "maximum_bending_strain": max_bending_strain,
        "estimated_bending_force_n": estimated_force_n,
        "force_comparison": force_comparison,
        "warnings": warnings,
    }
