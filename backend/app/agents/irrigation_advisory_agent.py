"""
Irrigation Advisory Specialist Agent
Synthesizes simulated soil moisture telemetry, historical multi-day moisture trends,
crop phenology, meteorological forecasts, and water management best practices.
Never executes hardware actuation (pumps/valves); advisory only.
"""
import re
from typing import List, Dict, Any
from app.agents.base import BaseAgent, AgentContext
from app.models.conversation import AgentResult
from app.tools.base import BaseTool


class IrrigationAdvisoryAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return "irrigation_advisory"

    @property
    def name(self) -> str:
        return "Irrigation Advisory Specialist"

    @property
    def description(self) -> str:
        return (
            "Analyzes simulated soil moisture, 7-day moisture trends, crop growth stage, and meteorological forecasts "
            "to formulate water management recommendations, over-irrigation precautions, and crop-specific irrigation regimes."
        )

    @property
    def permitted_tools(self) -> List[str]:
        return ["farm_telemetry", "latest_telemetry", "historical_telemetry", "weather_context", "crop_knowledge"]

    async def execute(
        self,
        context: AgentContext,
        tools: Dict[str, BaseTool],
    ) -> AgentResult:
        query_lower = context.query.lower()
        is_hindi = context.language.lower().startswith("hi") or bool(
            re.search(r"[\u0900-\u097F]", context.query)
        )
        zone_id = getattr(context, "zone_id", None) or "DEMO-ZONE-001"

        # 1. Retrieve latest telemetry
        tel_tool = tools.get("latest_telemetry") or tools.get("farm_telemetry")
        tel_data = await tel_tool.execute(zone_id=zone_id) if tel_tool else {}

        # Fail closed on unknown zone
        if tel_data.get("status") == "error":
            err_msg = (
                f"ज़ोन '{zone_id}' इस फार्म में पंजीकृत नहीं है। कृपया मान्य ज़ोन चुनें।"
                if is_hindi
                else f"Zone '{zone_id}' is not registered on this farm. Please select a valid zone."
            )
            return AgentResult(
                agent_id=self.agent_id,
                name=self.name,
                summary=err_msg,
                finding=err_msg,
                confidence=1.0,
                evidence=[f"Requested Zone: {zone_id}", "Status: Not Registered"],
                limitations=["Unknown zone requested."],
                status="completed",
            )

        # 2. Retrieve historical moisture trend
        hist_tool = tools.get("historical_telemetry")
        hist_data = await hist_tool.execute(zone_id=zone_id, parameter="soil_moisture_pct", time_range="7d") if hist_tool else {}

        # 3. Retrieve weather forecast
        weather_tool = tools.get("weather_context")
        weath_data = await weather_tool.execute() if weather_tool else {}

        crop = tel_data.get("crop", "wheat")
        growth_stage = tel_data.get("growth_stage", "Tillering")
        soil_type = tel_data.get("soil_type", "Clay-Loam")
        moisture = tel_data.get("soil_moisture_pct")
        soil_temp = tel_data.get("soil_temperature_c")
        ec = tel_data.get("electrical_conductivity_ds_m")
        ph = tel_data.get("ph")
        completeness_ratio = tel_data.get("completeness_ratio", "Telemetry available")
        tank_level = tel_data.get("water_tank_level_pct")
        rain_prob = weath_data.get("rain_probability_24h_pct", 0.0)
        trend_summary = hist_data.get("trend_summary", "Trend data unavailable")

        # Specific query topics
        is_first_irrigation = (
            any(w in query_lower for w in ["pehli sinchai", "first irrigation", "पहली सिंचाई", "पहला पानी", "1st irrigation", "first water"])
            or (any(w in query_lower for w in ["kab kare", "kab karni", "kab de", "timing", "schedule"]) and any(w in query_lower for w in ["irrigation", "sinchai", "water", "पानी", "सिंचाई"]))
            or any(w in context.query for w in ["पहली सिंचाई", "पहला पानी", "कब करें", "कब पानी दें", "कब सिंचाई"])
        )
        is_maize_query = any(w in query_lower for w in ["maize", "makka", "corn", "मक्का", "मक्के", "bhutta", "भुट्टा"])
        is_cotton_irrigation = any(w in query_lower for w in ["cotton", "कपास"]) and any(w in query_lower for w in ["manage", "kaise", "irrigation", "सिंचाई"])
        is_over_irrigation = any(w in query_lower for w in ["over-irrigation", "over irrigation", "jyada paani", "disadvantage", "nuksan", "हानि", "अत्यधिक सिंचाई"])
        is_monsoon = any(w in query_lower for w in ["monsoon", "barish", "बरसात", "मानसून", "precaution", "सावधानी"])

        # Check for user-specified moisture in query (e.g. "40% नमी पर पानी देना चाहिए या नहीं?")
        specified_moisture_match = re.search(r"(\d{1,2}(?:\.\d+)?)\s*(?:%|प्रतिशत)?\s*(?:नमी|moisture)", context.query, re.IGNORECASE) or re.search(r"(?:नमी|moisture)\s*(\d{1,2}(?:\.\d+)?)", context.query, re.IGNORECASE)
        query_specified_moisture = float(specified_moisture_match.group(1)) if specified_moisture_match else None

        evidence: List[str] = [
            f"Zone: {tel_data.get('zone_name', zone_id)}",
            f"Crop: {crop} ({growth_stage}, Soil: {soil_type})",
            f"Current Soil Moisture: {moisture:.1f}% (Simulated FertoBot probe)" if moisture is not None else "Current Soil Moisture: Unavailable",
            f"7-Day Trend: {trend_summary}",
            f"Soil Temperature: {soil_temp:.1f}°C" if soil_temp is not None else "Soil Temperature: Unavailable",
            f"Electrical Conductivity (EC): {ec:.2f} dS/m" if ec is not None else "EC: Unavailable",
            f"Soil pH: {ph:.1f}" if ph is not None else "Soil pH: Unavailable",
            f"Water Reservoir Storage: {tank_level:.1f}%" if tank_level is not None else "Water Reservoir Storage: Unavailable",
            f"Forecasted Rain Probability: {rain_prob:.0f}% in next 24h (Live Open-Meteo)",
            f"Telemetry Completeness: {completeness_ratio}",
            "Data Source: Simulated Soil Telemetry + Live Meteorological Forecast",
        ]

        limitations: List[str] = [
            "Simulated moisture reflects sensor depth (15cm). Subsoil hydraulic gradient is unmonitored.",
            "Water delivery valves remain locked (no actuation authority).",
            "Automated valve actuation is prohibited; farmer must physically manage irrigation controls.",
        ]

        if is_maize_query:
            limitations.append("Maize is not registered in any monitored sensor zone on this farm (farm zones: Zone 1 Wheat, Zone 2 Cotton, Zone 3 Tomato, Zone 4 Mustard).")
            limitations.append("Moisture percentage queried reflects farmer-reported input, not calibrated on-farm telemetry.")
            eval_m_str = f"{query_specified_moisture:.0f}%" if query_specified_moisture is not None else "40%"
            if is_hindi:
                summary = (
                    f"मक्का आपके खेत के पंजीकृत सेंसर ज़ोन में नहीं है (सेंसर ज़ोन केवल गेहूं, कपास, टमाटर और सरसों के हैं)। "
                    f"आपके द्वारा बताई गई {eval_m_str} नमी की रीडिंग किसान-प्रदत्त है। केवल नमी के प्रतिशत से सिंचाई का पक्का निर्णय नहीं लिया जा सकता, "
                    "क्योंकि यह मिट्टी की बनावट (हल्की बलुई या भारी दोमट), सेंसर की गहराई और फसल की अवस्था पर निर्भर करता है। "
                    "मक्का में मंजर निकलने (tasseling) और सिल्क निकलने (silking) की क्रांतिक अवस्थाओं पर नमी की कमी सबसे अधिक नुकसानदायक होती है। "
                    "जलभराव से बचते हुए हल्की सिंचाई करें। सटीक सलाह के लिए कृपया अपनी मिट्टी का प्रकार और मक्का की वर्तमान वृद्धि अवस्था बताएं।"
                )
            else:
                summary = (
                    f"Maize is not registered in any monitored sensor zone on your farm (registered zones: Zone 1 Wheat, Zone 2 Cotton, Zone 3 Tomato, Zone 4 Mustard). "
                    f"The queried {eval_m_str} soil moisture represents farmer-provided input rather than calibrated on-farm telemetry. "
                    "A moisture percentage alone cannot definitively dictate irrigation without establishing soil texture, sensor depth, root-zone depth, and crop growth stage. "
                    "Moisture stress is most damaging during flowering stages—tasseling and silking/grain filling—while ensuring proper furrow drainage as maize is intolerant of standing water. "
                    "To provide accurate guidance, please share your soil texture and current crop growth stage."
                )

        elif is_first_irrigation and ("wheat" in query_lower or "गेहूं" in context.query or "गेहु" in context.query or "wheat" in crop.lower()):
            moist_str = f"{moisture:.1f}%" if moisture is not None else "उपलब्ध नहीं"
            if is_hindi:
                summary = (
                    "गेहूं में पहली सिंचाई सामान्यतः 'ताज मूल अवस्था' (CRI - Crown Root Initiation) पर की जाती है, जो अनुकूल परिस्थितियों में प्रायः बुवाई के 20 से 25 दिन बाद आती है। "
                    "हालांकि, यह समय बुवाई की गहराई, तापमान और किस्म के अनुसार बदल सकता है। वैज्ञानिक अध्ययनों के अनुसार, क्राउन जड़ें बनते समय गंभीर सूखे से पैदावार में 30 से 40 प्रतिशत तक की कमी का जोखिम हो सकता है। "
                    f"फ़र्टोबॉट सेंसर बुवाई की तारीख ट्रैक नहीं करते, लेकिन वर्तमान में आपके गेहूं खेत (Zone 1) की मिट्टी की नमी {moist_str} है। "
                    "पौधों के आधार पर ताज जड़ों की जांच करें और यदि ऊपरी मिट्टी सूखी लगे तो हल्की सिंचाई करें।"
                )
            else:
                moist_en = f"{moisture:.1f}%" if moisture is not None else "unavailable"
                summary = (
                    "In wheat, the first irrigation is typically scheduled at Crown Root Initiation (CRI), which under standard conditions generally occurs around 20 to 25 days after sowing (DAS). "
                    "However, exact timing varies with sowing depth, ambient temperature, variety, and initial seedbed moisture. Agronomic literature indicates that severe moisture deficit during crown root formation may risk potential yield penalties of up to 30% to 40%. "
                    f"While FertoBot sensors monitor soil moisture (currently {moist_en} in Zone 1 Wheat), they do not track calendar sowing dates. "
                    "Inspect the crown roots at the shoot base: if crown roots have initiated and the topsoil is dry, apply a light to moderate irrigation."
                )

        elif is_cotton_irrigation:
            if is_hindi:
                summary = (
                    "कॉटन (कपास) की सिंचाई प्रबंधन की प्रमुख वैज्ञानिक विधियां: "
                    "1. कॉटन को जलभराव बिल्कुल सहन नहीं होता, इसलिए हल्की व मध्यम सिंचाई दें (ड्रिप सिंचाई सर्वोत्तम है)। "
                    "2. क्रांतिक अवस्थाएं (Critical Stages): फूल आने (Flowering) और गूलर/टिंडे बनने (Boll Development) के समय मिट्टी में नमी की कमी न होने दें। "
                    f"वर्तमान में कॉटन ज़ोन की नमी {moisture:.1f}% है। गूलर खिलने के समय सिंचाई धीरे-धीरे कम करें।"
                )
            else:
                summary = (
                    "Cotton irrigation management guidelines: "
                    "1. Cotton is highly sensitive to waterlogging; avoid excessive flooding and prefer furrow or drip irrigation. "
                    "2. Critical growth stages: Maintain adequate soil moisture during squaring, peak flowering, and boll development. "
                    f"Current cotton zone moisture is {moisture:.1f}%. Gradually taper off irrigation as bolls begin opening to prevent fiber staining."
                )

        elif is_over_irrigation:
            if is_hindi:
                summary = (
                    "अत्यधिक सिंचाई (Over-irrigation) के 4 प्रमुख गंभीर नुकसान: "
                    "1. जड़ों का दम घुटना (Root Hypoxia): मिट्टी के छिद्रों में हवा खत्म होने से जड़ें सांस नहीं ले पातीं और पोषण रुक जाता है। "
                    "2. जड़ गलन और फफूंद (Root Rot): गीली मिट्टी में फ्यूजेरियम और डैम्पिंग-ऑफ जैसी बीमारियां फैलती हैं। "
                    "3. पोषक तत्वों का लीचिंग: पानी में घुलनशील नाइट्रोजन और पोटाश जड़ों से नीचे बह जाते हैं। "
                    "4. लवणता (Salinity): भूमिगत खारा पानी ऊपर आकर मिट्टी की सतह पर सफेद नमक की परत जमा देता है।"
                )
            else:
                summary = (
                    "Major agronomic disadvantages of over-irrigation: "
                    "1. Root Hypoxia & Asphyxiation: Standing water displaces soil oxygen, preventing cellular respiration and nutrient uptake. "
                    "2. Root Rot Pathogens: Promotes virulent soil-borne fungi (Pythium, Fusarium, Phytophthora). "
                    "3. Nutrient Leaching: Soluble nitrates and potassium are washed beyond the active root zone into groundwater. "
                    "4. Secondary Salinization: High water tables pull subsoil salts to the surface through capillary action."
                )

        elif is_monsoon:
            if is_hindi:
                summary = (
                    "मानसून (Monsoon) के दौरान खेती में आवश्यक सावधानियां: "
                    "1. खेत के चारों तरफ जल निकासी (Drainage trenches) साफ रखें ताकि 12 घंटे से अधिक पानी न भरे। "
                    "2. सब्जियों, कपास और मक्का को उठी हुई क्यारियों (Raised Bed / Ridge) पर लगाएं। "
                    "3. भारी बारिश के तुरंत पहले यूरिया या घुलनशील खाद का छिड़काव न करें ताकि खाद बह न जाए। "
                    "4. नमी व उमस से फफूंद फैलती है, अतः मौसम साफ होते ही ट्राइकोडर्मा या बोर्डो मिश्रण का सुरक्षात्मक छिड़काव करें।"
                )
            else:
                summary = (
                    "Key agricultural precautions during monsoon: "
                    "1. Drainage Maintenance: Ensure perimeter furrows and drainage ditches are clear to evacuate excess runoff within 12 hours. "
                    "2. Raised Bed Planting: Cultivate sensitive crops (vegetables, cotton, maize) on broad ridges to elevate root zones above saturated furrows. "
                    "3. Postpone Fertilizer Broadcast: Avoid top-dressing urea immediately before heavy showers to prevent leaching and wash-off. "
                    "4. Preventive Bio-Fungicide: High ambient humidity triggers foliar blights; apply prophylactic bio-fungicide (Trichoderma/Pseudomonas) during dry spells."
                )

        elif moisture >= 60.0:
            if ec > 2.0:
                if is_hindi:
                    summary = (
                        f"{tel_data.get('zone_name', zone_id)} में मिट्टी की नमी {moisture:.1f}% (संतृप्त) है और विद्युत चालकता (EC) {ec:.1f} dS/m (अत्यधिक लवणता जोखिम) है। "
                        "उच्च लवणता और अतिरिक्त नमी के कारण परासरणी तनाव (Osmotic stress) और जड़ सड़न का खतरा है। "
                        "तत्काल सिंचाई रोकें, जल निकासी सुनिश्चित करें, और बाद में कम खारे पानी से लीचिंग (Leaching) द्वारा लवण बहाएं।"
                    )
                else:
                    summary = (
                        f"In {tel_data.get('zone_name', zone_id)}, soil moisture is saturated at {moisture:.1f}% with elevated EC at {ec:.1f} dS/m (salinity hazard). "
                        "High EC induces osmotic stress preventing root water uptake despite saturated soil. "
                        "Halt all irrigation immediately, ensure furrow drainage, and later apply a leaching fraction with low-saline water."
                    )
            else:
                if is_hindi:
                    summary = (
                        f"{tel_data.get('zone_name', zone_id)} में मिट्टी की नमी {moisture:.1f}% है, जो अत्यधिक गीली (संतृप्त) स्थिति दर्शाती है। "
                        "अभी किसी भी प्रकार की सिंचाई न करें। खेत में उचित जल निकासी सुनिश्चित करें ताकि जड़ों का दम न घुटे।"
                    )
                else:
                    summary = (
                        f"Soil moisture in {tel_data.get('zone_name', zone_id)} is high at {moisture:.1f}% (saturation risk). "
                        "Do NOT irrigate. Ensure field drainage channels are clear to prevent root hypoxia."
                    )
        elif moisture >= 42.0 and rain_prob >= 40.0:
            if is_hindi:
                summary = (
                    f"वर्तमान में {tel_data.get('zone_name', zone_id)} में मिट्टी की नमी {moisture:.1f}% अनुकूल स्तर पर है "
                    f"और 7 दिनों में {trend_summary}। अगले 24 घंटों में {rain_prob:.0f}% बारिश की संभावना है। "
                    "अतः आज अपनी फसल में सिंचाई स्थगित करने की सलाह दी जाती है ताकि जलभराव और पोषक तत्वों के बहने से बचा जा सके।"
                )
            else:
                summary = (
                    f"Current soil moisture in {tel_data.get('zone_name', zone_id)} is optimal at {moisture:.1f}% "
                    f"({trend_summary}). With a {rain_prob:.0f}% probability of rain within 24 hours, "
                    "irrigation should be postponed to avoid root zone waterlogging and nutrient leaching."
                )
        elif moisture < 35.0:
            if is_hindi:
                summary = (
                    f"{tel_data.get('zone_name', zone_id)} में मिट्टी की नमी घटकर {moisture:.1f}% हो गई है "
                    f"({trend_summary})। वर्षा की संभावना केवल {rain_prob:.0f}% है। "
                    f"{crop} की {growth_stage} अवस्था में नमी की कमी से बचाने के लिए हल्की से मध्यम सिंचाई की सिफारिश की जाती है। "
                    f"पानी का टैंक {tank_level:.1f}% भरा है।"
                )
            else:
                summary = (
                    f"Soil moisture in {tel_data.get('zone_name', zone_id)} has dropped to {moisture:.1f}% "
                    f"({trend_summary}) with low rain probability ({rain_prob:.0f}%). "
                    f"Targeted irrigation is recommended to prevent moisture deficit stress during {growth_stage}. "
                    f"Water tank storage is at {tank_level:.1f}%."
                )
        else:
            if is_hindi:
                summary = (
                    f"मिट्टी की नमी {moisture:.1f}% संतुलित है ({trend_summary})। "
                    f"मौसम के पूर्वानुमान ({rain_prob:.0f}% वर्षा) को देखते हुए आज अतिरिक्त सिंचाई की आवश्यकता नहीं है।"
                )
            else:
                summary = (
                    f"Soil moisture in {tel_data.get('zone_name', zone_id)} is stable at {moisture:.1f}% ({trend_summary}). "
                    f"Considering weather forecasts ({rain_prob:.0f}% rain), no immediate irrigation adjustment is needed."
                )

        return AgentResult(
            agent_id=self.agent_id,
            name=self.name,
            status="completed",
            summary=summary,
            evidence=evidence,
            limitations=limitations,
            data={
                "zone_id": zone_id,
                "crop": crop,
                "soil_moisture_pct": moisture,
                "soil_temperature_c": soil_temp,
                "electrical_conductivity_ds_m": ec,
                "ph": ph,
                "completeness_ratio": completeness_ratio,
                "water_tank_level_pct": tank_level,
                "rain_probability_24h_pct": rain_prob,
                "trend_summary": trend_summary,
                "actuation_permitted": False,
                "is_simulated": True,
            },
        )
