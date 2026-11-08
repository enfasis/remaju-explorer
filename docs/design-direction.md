# Recognizably REMAJU

A practical, contemporary Peruvian auction explorer. Optimize for finding properties, comparing prices, checking deadlines, and understanding judicial proceedings—not for looking institutional, luxurious, or unlike an AI-generated concept. This remains an independent information tool, not an official judicial service.

## Identity

Use neutral white surfaces on a light gray canvas, with a charcoal dark theme. Moderate rounding and a little depth are useful for search and the auction summary; avoid both floating everything and flattening everything.

Vivid crimson (`#D7263D`) anchors auction identity. Gold (`#F5C518`) marks financial content; blue (`#2D6CDF`) identifies phases and process navigation; green (`#178A5B`) identifies ongoing/valid states; teal (`#188B8A`) identifies geography. Use accessible semantic foregrounds on pale backgrounds where small text needs more contrast. Color should help people recognize information, not assign equal prominence to every label.

`src/web/public/remaju-mark.svg` is a single compact brand mark using stepped enclosures, nested paths, and contrasting colors inspired by the textile reference. It is original geometry, not a reproduction of an authenticated Chavín symbol. Keep it with the primary navigation brand, rather than repeating it as trim, wallpaper, or a stamp beside every heading.

## Typography and composition

Use the existing contemporary sans-serif throughout the application. Titles should be compact, with price and published status close to the property name. Use tabular figures for amounts and dates. Prefer weights 400, 500, and 700; avoid oversized display headings, tiny uppercase captions, and spacious presentation-like hero layouts.

The listing stays table-first, with no property card view: prominent search, two essential filters, expandable advanced filters, and one Table/Map control. Keep active advanced-filter counts visible. Retain clear auction links, grouped locations, right-aligned money, and the distinction between offer dates and phase-end dates. Keep rows dense enough for comparison.

The detail summary puts identity, published status, convocatoria, and price together. A compact process row carries one blue phase chip and the published deadline, including Peru time. On small screens the content stacks without large gaps. Do not imply an expired or suspended schedule is a live opportunity.

Financial amounts use aligned rows with a gold accent. The schedule uses a blue-accented timeline. Property facts have a quiet white surface; legal descriptions retain a readable text column; judicial fields remain structured. Section headings use normal-sized, sentence-case text. Share useful spacing and alignment without forcing every section into an identical visual treatment.

## Credibility and status

The listing state and tracking events have different provenance. Keep the published listing state consistent in the listing and hero, with tracking state as a fallback only when the listing provides none. When a recorded state differs, show its source, convocatoria, and date where available. Preserve the full history; never overwrite datasets to reconcile a visual inconsistency.

Only recognized ongoing statuses receive green emphasis. Finished and unknown states are neutral; suspended, deserted, cancelled, or annulled states receive muted red; pending states receive warning text. Keep status words, not just color. Badges are allowed when they aid scanning: one secondary phase chip is useful; a collection of equally prominent colorful pills is not.

Dates and times refer to Peru. Mark past schedules as concluded and future phases as scheduled. Keep source verification visible and avoid duplicated currency amounts when conversion is unavailable. Respect reduced motion, keyboard focus, and horizontal table scrolling without page overflow at narrow widths.
