from pydantic import BaseModel, Field, model_validator
from typing import List

# Allowed values (taken from dataset/model context)
ALLOWED_OPERAS = {
    "Aerolineas Argentinas",
    "Air Canada",
    "Air France",
    "Alitalia",
    "American Airlines",
    "Austral",
    "Avianca",
    "British Airways",
    "Copa Air",
    "Delta Air Lines",
    "Gol Trans",
    "Grupo LATAM",
    "Iberia",
    "K.L.M.",
    "Latin American Wings",
    "Oceanair Linhas Aereas",
    "PLUNA",
    "Sky Airline",
    "United Airlines",
    "Qantas Airways"
}
ALLOWED_TIPOVUELO = {"N", "I"}
ALLOWED_MES = set(range(1, 13))

class FlightItem(BaseModel):
    OPERA: str = Field(..., description="Airlines company name", example="Aerolineas Argentinas")
    TIPOVUELO: str = Field(..., description="Flight type: N (National) or I (International)", example="N")
    MES: int = Field(..., description="Month of the flight (1-12)", example=3)

    @model_validator(mode='after')
    def validate_inputs(self):
        opera = self.OPERA
        tipovuelo = self.TIPOVUELO
        mes = self.MES
        
        if opera not in ALLOWED_OPERAS:
            raise ValueError(f"Invalid OPERA: {opera}. Allowed values: {list(ALLOWED_OPERAS)}")
        if tipovuelo not in ALLOWED_TIPOVUELO:
            raise ValueError(f"Invalid TIPOVUELO: {tipovuelo}. Allowed values: {list(ALLOWED_TIPOVUELO)}")
        if mes not in ALLOWED_MES:
            raise ValueError(f"Invalid MES: {mes}. Allowed values: {list(ALLOWED_MES)}")
        
        return self

class FlightsRequest(BaseModel):
    flights: List[FlightItem] = Field(..., description="List of flight data to predict delays for", example=[
        {
            "OPERA": "Aerolineas Argentinas",
            "TIPOVUELO": "N",
            "MES": 3
        }
    ])
