from app import calculate


def test_tfl_and_pn_rate_math():
    result = calculate({
        "dosing_weight_kg": 2,
        "tfl_ml_per_kg_day": 120,
        "ivfe_dose_g_kg_day": 1,
        "non_pn_art_line_ml_hr": 0.5,
        "non_pn_uvc_ml_hr": 0.5,
        "non_pn_picc_ml_hr": 0,
        "non_pn_continuous_meds_ml_hr": 0,
        "non_pn_bolus_meds_ml_day": 24,
    })
    assert result["values"]["tfl_ml_day"] == 240
    assert result["values"]["tfl_ml_hr"] == 10.0
    assert result["values"]["ivfe_ml_hr"] == 0.42
    assert result["values"]["non_pn_bolus_meds_ml_hr"] == 1.0
    assert result["values"]["total_non_pn_ml_hr"] == 2.42
    assert result["values"]["pn_rate_ml_hr"] == 7.6


def test_protein_and_gir_math():
    result = calculate({
        "dosing_weight_kg": 2,
        "protein_g_kg_day": 3,
        "dextrose_percent": 10,
        "tfl_ml_per_kg_day": 120,
    })
    assert result["values"]["protein_g_day"] == 6
    assert result["values"]["protein_kcal_day"] == 24
    assert result["values"]["tpn_gir"] == 8.35


def test_peripheral_warning():
    result = calculate({
        "dosing_weight_kg": 1,
        "dextrose_percent": 15,
        "access_type": "Peripheral",
        "tfl_ml_per_kg_day": 120,
    })
    assert any("Peripheral" in warning for warning in result["warnings"])
