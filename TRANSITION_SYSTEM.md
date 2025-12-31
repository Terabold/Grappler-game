# Room Transition System - Final Documentation

## How It Works Now (Correct Behavior)

### **1. One Spawner Per Room**
Each room has a spawn point defined in its JSON file (in the "objects" layer).

### **2. When You Die**
You respawn at **the current room's spawn point**.
- Die in Room 1 → Respawn at Room 1 spawn
- Die in Room 2 → Respawn at Room 2 spawn
- Die in Room 3 → Respawn at Room 3 spawn

### **3. Advancing to a New Room (Forward Progression)**
When you move from a lower-numbered room to a higher-numbered room:
- **Room 1 → Room 2**: You **teleport** to Room 2's spawn point
- **Room 2 → Room 3**: You **teleport** to Room 3's spawn point

**Behavior:**
- ✅ Velocity is **zeroed** (you stop)
- ✅ Position is **set to spawn**
- ✅ Respawn checkpoint updates to this room's spawn

### **4. Going Back to Previous Room (Backward Movement)**
When you return to a lower-numbered room:
- **Room 3 → Room 2**: You **walk naturally** through the boundary
- **Room 2 → Room 1**: You **walk naturally** through the boundary

**Behavior:**
- ✅ Velocity is **preserved** (you keep momentum)
- ✅ Position is **nudged** 8px into the room at the boundary
- ✅ Respawn checkpoint updates to this room's spawn (in case you die)

## Technical Details

### Detection Method
Transitions trigger when the player's hitbox overlaps with an adjacent room's boundary.

The code checks:
```python
is_forward = target_room.room_id > current_room.room_id
```

### Room IDs
- `room_01` < `room_02` < `room_03` (alphabetical/numerical ordering)

### Momentum Preservation
```python
player.start_transition(direction, keep_momentum=not is_forward)
```
- Forward: `keep_momentum=False` → velocity zeroed
- Backward: `keep_momentum=True` → velocity preserved

### Nudge Distance
When entering naturally, the player is pushed 8 pixels into the room to prevent immediately re-triggering the transition (hysteresis).

## Examples

### Scenario 1: New Room
You're in Room 1, walk right into Room 2:
1. Transition detected (Room 1 → Room 2, forward)
2. Camera slides to Room 2
3. Player **teleports** to Room 2's spawn point (velocity = 0)
4. Checkpoint set to Room 2 spawn
5. If you die, you respawn at Room 2 spawn

### Scenario 2: Backtracking
You're in Room 2, walk left back to Room 1:
1. Transition detected (Room 2 → Room 1, backward)
2. Camera slides to Room 1
3. Player position **nudged** to Room 1's right edge (velocity kept!)
4. Checkpoint set to Room 1 spawn
5. You keep moving left naturally
6. If you die, you respawn at Room 1 spawn (not where you entered)

### Scenario 3: Death
You're exploring Room 2, hit spikes:
1. `player.dead = True`
2. `room_manager.respawn_player(player)` called
3. Player position set to Room 2's spawn point
4. Velocity zeroed
5. You're back at Room 2 spawn

## Summary Table

| Situation | Destination | Position | Velocity | Checkpoint |
|-----------|-------------|----------|----------|------------|
| **Advance (1→2)** | Room 2 | Spawn | Zeroed | Room 2 spawn |
| **Advance (2→3)** | Room 3 | Spawn | Zeroed | Room 3 spawn |
| **Retreat (3→2)** | Room 2 | Boundary+8px | Kept | Room 2 spawn |
| **Retreat (2→1)** | Room 1 | Boundary+8px | Kept | Room 1 spawn |
| **Die in Room X** | Room X | Spawn | Zeroed | No change |
