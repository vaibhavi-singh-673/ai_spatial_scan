# Adversarial capture matrix

Use the same room geometry and measured ground truth where possible. Record the
condition as a manifest tag and report it separately from clean-room results.

| Condition | Controlled setup | Evidence to collect | Current status |
|---|---|---|---|
| Mirrors | Large wall mirror and reflective furniture | Capture, false-wall notes, dimension errors | REQUIRED |
| Glass | Window or glass door with visible frame | Opening detection and scale failures | REQUIRED |
| Wet-look surface | Glossy tile or wet floor patch | Depth holes and plane residuals | REQUIRED |
| Low light | Same room with reduced lighting | Decode rate and geometry degradation | REQUIRED |
| Clutter | Furniture, boxes, textiles, plants | Occlusion and footprint errors | REQUIRED |
| Occlusion | Partially blocked wall/opening | Missing-measurement diagnostics | REQUIRED |
| Fast motion | Deliberately fast yaw pass | Blur, tracking, and drift behavior | REQUIRED |

Do not convert a failed or missing condition into a passing aggregate score.