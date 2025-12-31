# SIMPLIFIED SPAWN SYSTEM

## What You Have Now (Ultra Simple)

### Each Room Has:
- **1 spawn block** (placed in Tiled editor with type/name containing "spawn")
- That's it. Nothing else.

### Behavior:

1. **Die anywhere** → Respawn at current room's spawn ✅
2. **Advance to new room** (Room 1→2→3) → Teleport to that room's spawn ✅  
3. **Go back** (Room 3→2→1) → Walk naturally through boundary (keep momentum) ✅

## What Was Removed:

- ❌ Entry points system
- ❌ Multiple entry configurations  
- ❌ "from_room" properties
- ❌ Direction-based entries (left_entry, right_entry, etc.)
- ❌ Entry point pop-up menus in editor

## How To Use:

In Tiled, just add ONE rectangle in the "objects" layer per room:
- **Name**: "spawn"  
- **Type**: "spawn"  
- Place it where you want the player to start/respawn

That's all you need!
