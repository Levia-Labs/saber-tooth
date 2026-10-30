# generate

The Generate page's cards, in the beat-analyser visual language.

1. `AddCard.tsx`: the YouTube link field and audio file drop, with inline validation.
2. `AnalyseCard.tsx`: the generate job's state: status chip (queue number while queued), stage list, and an Open Jobs link.
3. `StageList.tsx`: the stages (Download or Upload, Analyse beats, Map, Fix, Write) derived from the job's status and progress.
