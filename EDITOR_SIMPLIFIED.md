# Room Editor - NOW SIMPLIFIED!

## What I've Done So Far:

1. **✅ Removed entry_points** from RoomData class
2. **✅ Added simple spawn** (just x, y coordinates)
3. **✅ Updated save/load** to use spawn instead of entry
4. **✅ Fixed room JSON files** to have proper spawn objects

## What Still Needs Fixing in roomeditor.py:

The editor UI (around line 572+) still has:
- EntryPointEditor dialog (the popup you hate)
- UI buttons for entry points
- Drawing code for entry points

I'm simplifying this now so you can just:
**Press 'S' key → Click to place spawn → Done!**

## In the meantime, you can manually edit room JSON files:

Just set the spawn object like this:
```json
{
  "name": "objects",
  "type": "objectgroup",
  "objects": [
    {
      "name": "spawn",
      "type": "spawn",
      "x": 100,  // Pixel position (not tile)
      "y": 200   
    }
  ]
}
```

The game will load this and teleport you there!
