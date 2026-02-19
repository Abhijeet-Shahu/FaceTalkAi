import enum
import logging
from typing import Annotated

logger = logging.getLogger("temperature-control")
logger.setLevel(logging.INFO)


class Zone(enum.Enum):
    LIVING_ROOM = "living_room"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    OFFICE = "office"


class AssistantFnc:
    def __init__(self) -> None:
        self._temperature = {
            Zone.LIVING_ROOM: 22,
            Zone.BEDROOM: 20,
            Zone.KITCHEN: 24,
            Zone.BATHROOM: 23,
            Zone.OFFICE: 21,
        }

    def get_tools(self):
        """Return OpenAI Realtime API function tools for temperature control"""
        return [
            {
                "type": "function",
                "name": "get_temperature",
                "description": "Get the temperature in a specific room",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "zone": {
                            "type": "string",
                            "enum": [z.value for z in Zone],
                            "description": "The specific zone"
                        }
                    },
                    "required": ["zone"]
                }
            },
            {
                "type": "function",
                "name": "set_temperature",
                "description": "Set the temperature in a specific room",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "zone": {
                            "type": "string",
                            "enum": [z.value for z in Zone],
                            "description": "The specific zone"
                        },
                        "temp": {
                            "type": "integer",
                            "description": "The temperature to set"
                        }
                    },
                    "required": ["zone", "temp"]
                }
            }
        ]

    def get_temperature(self, zone: str):
        """Get the temperature in a specific room"""
        logger.info("get temp - zone %s", zone)
        temp = self._temperature[Zone(zone)]
        return f"The temperature in the {zone} is {temp}C"

    def set_temperature(self, zone: str, temp: int):
        """Set the temperature in a specific room"""
        logger.info("set temp - zone %s, temp: %s", zone, temp)
        self._temperature[Zone(zone)] = temp
        return f"The temperature in the {zone} is now {temp}C"

    def execute_function(self, function_name: str, arguments: dict):
        """Execute a function call"""
        if function_name == "get_temperature":
            return self.get_temperature(arguments["zone"])
        elif function_name == "set_temperature":
            return self.set_temperature(arguments["zone"], arguments["temp"])
        else:
            return f"Unknown function: {function_name}"
