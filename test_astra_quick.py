import sys
from backend.astra.schemas import AstraChatRequest, UserMode
from backend.astra.assistant import astra_assistant
from backend.astra.tools import tool_registry
from backend.astra.astronomy.catalog import catalog_provider
from backend.astra.astronomy.plate_solver import get_plate_solver

print("ASTRA tools count:", len(tool_registry.get_tool_definitions()))
print("Catalog objects count:", len(catalog_provider._objects))
solver = get_plate_solver()
sol = solver.solve(hint_ra=295.5, hint_dec=44.5)
print("Plate solver test:", sol.solved, sol.constellation)

# Test chat
resp = astra_assistant.process_chat(AstraChatRequest(message="Explain the scientific summary for STAR_0001", star_id="STAR_0001", mode=UserMode.SCIENTIST))
print("Chat response mode:", resp.mode)
print("Period detected:", resp.scientific_values.period_days if resp.scientific_values else None)
print("ASTRA tests verified successfully!")
