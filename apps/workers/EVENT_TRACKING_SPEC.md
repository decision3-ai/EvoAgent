# V2.1 Event Tracking Spec

## DB — jedna tablica
analytics_events:
  id            uuid PK
  workspace_id  uuid FK workspaces
  session_id    uuid FK sessions nullable
  message_id    uuid FK messages nullable
  event_type    varchar  # code_copy | completion
  metadata      jsonb    # code_block_index, language, etc.
  created_at    timestamp

## Duplicate protection
- 1 code_copy per message_id per workspace per day
- 1 completion per session_id max

## Events
1. code_copy
   metadata: { code_block_index, language }

2. completion
   UI text: "Did this solve it?" + "✅ Solved" button

## return_rate — iz sessions.created_at (bez novog eventa)
same_day_return  = sessions isti dan
next_day_return  = session sljedeći dan
7_day_return     = session unutar 7 dana

## Fitness V3 formula
fitness =
  0.30 * feedback_score +
  0.25 * return_rate +
  0.20 * code_copy_score +
  0.15 * completion_score -
  0.10 * penalty_score

## Implementacija redoslijed
1. Backend — analytics_events tablica + endpoint
2. Frontend — Copy button šalje event
3. Frontend — "Did this solve it?" button
4. Nightly — recompute return_rate iz sessions
5. Update compute_fitness formula
