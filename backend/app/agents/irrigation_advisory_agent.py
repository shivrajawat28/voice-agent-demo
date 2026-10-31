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

        # 2. Retrieve historical moisture trend
        hist_tool = tools.get("historical_telemetry")
        hist_data = await hist_tool.execute(zone_id=zone_id, parameter="soil_moisture_pct", time_range="7d") if hist_tool else {}

        # 3. Retrieve weather forecast
        weather_tool = tools.get("weather_context")
        weath_data = await weather_tool.execute() if weather_tool else {}

        crop = tel_data.get("crop", "wheat")
        growth_stage = tel_data.get("growth_stage", "Tillering")
        soil_type = tel_data.get("soil_type", "Clay-Loam")
        moisture = tel_data.get("soil_moisture_pct", 48.2)
        soil_temp = tel_data.get("soil_temperature_c", 22.4)
        ec = tel_data.get("electrical_conductivity_ds_m", 1.2)
        ph = tel_data.get("ph", 6.8)
        completeness_ratio = tel_data.get("completeness_ratio", "7/7 parameters available")
        tank_level = tel_data.get("water_tank_level_pct", 82.0)
        rain_prob = weath_data.get("rain_probability_24h_pct", 65.0)
        trend_summary = hist_data.get("trend_summary", "Stable moisture levels")

        # Specific query topics
        is_cotton_irrigation = any(w in query_lower for w in ["cotton", "कपास"]) and any(w in query_lower for w in ["manage", "kaise", "irrigation", "सिंचाई"])
        is_over_irrigation = any(w in query_lower for w in ["over-irrigation", "over irrigation", "jyada paani", "disadvantage", "nuksan", "हानि", "अत्यधिक सिंचाई"])
        is_monsoon = any(w in query_lower for w in ["monsoon", "barish", "बरसात", "मानसून", "precaution", "सावधानी"])

        evidence: List[str] = [
            f"Zone: {tel_data.get('zone_name', zone_id)}",
            f"Crop: {crop} ({growth_stage}, Soil: {soil_type})",
            f"Current Soil Moisture: {moisture:.1f}% (Simulated FertoBot probe)",
            f"7-Day Trend: {trend_summary}",
            f"Soil Temperature: {soil_temp:.1f}°C",
            f"Electrical Conductivity (EC): {ec:.2f} dS/m (Salinity: {'Elevated / Salinity Risk' if ec > 2.0 else 'Optimal / Normal'})",
            f"Soil pH: {ph:.1f}",
            f"Water Reservoir Storage: {tank_level:.1f}%",
            f"Forecasted Rain Probability: {rain_prob:.0f}% in next 24h (Live Open-Meteo)",
            f"Telemetry Completeness: {completeness_ratio}",
            "Data Source: Simulated Soil Telemetry + Live Meteorological Forecast",
        ]

        limitations: List[str] = [
            "Simulated moisture reflects sensor depth (15cm). Subsoil hydraulic gradient is unmonitored.",
            "Water delivery valves remain locked (no actuation authority).",
            "Automated valve actuation is prohibited; farmer must physically manage irrigation controls.",
        ]

        if is_cotton_irrigation:
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
