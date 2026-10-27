# Map format

saber-tooth reads Info v2.0.0, v2.1.0 and v4, and difficulty v2, v3 and v4. It writes Info v2.1.0 and difficulty v3.3.0 only. Only the Standard characteristic is handled.

## Files in the wild

1. Info: `Info.dat` or `info.dat`.
2. Difficulty: `<Diff>.dat`, `<Diff>Standard.dat` or `<Diff>.beatmap.dat`.
3. Audio: `.egg` or `.ogg`.
4. Cover: `.jpg` or `.png`.

## Difficulty keys

| Item  | v2                                                                     | v3                                                                 | v4                                                               |
| ----- | ---------------------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------- |
| note  | `_time,_lineIndex,_lineLayer,_type(0 red,1 blue,3 bomb),_cutDirection` | `colorNotes[{b,x,y,c,d,a}]`, `bombNotes[{b,x,y}]`                  | `colorNotes[{b,i}]` + `colorNotesData[{x,y,c,d,a}]`              |
| wall  | `_time,_lineIndex,_type(0 full,1 crouch),_duration,_width`             | `obstacles[{b,x,y,d,w,h}]`                                         | `obstacles[{b,i}]` + `obstaclesData[{d,x,y,w,h}]`                |
| event | `_events[{_time,_type,_value,_floatValue}]`, type 5 = boost            | `basicBeatmapEvents[{b,et,i,f}]`, `colorBoostBeatmapEvents[{b,o}]` | lightshow file `basicEvents[{b,i}]` + `basicEventsData[{t,i,f}]` |
| bpm   | `_customData._BPMChanges[{_time,_BPM}]` or `_events` type 100          | `bpmEvents[{b,m}]`                                                 | ignored in v1 (see TODO)                                         |

## Conversions

1. Vanilla only. Mapping Extensions and Noodle positions are unsupported: a note or bomb with x outside 0-3, y outside 0-2 or a cut direction outside 0-8 (including 1000+ precision directions) makes the map unreadable. A bpm that is not positive and finite does too.

2. A v2 crouch wall (`_type` 1) maps to `y=2`, height 3. A v2 full wall maps to `y=0`, height 5.
3. v4 colour scheme colours are hex strings `"RRGGBBAA"`. They convert to `{r,g,b,a}` floats.
4. Tempo changes are sorted by beat only. When two changes share a beat, the later one in source order wins.

## Info keys

1. v2: `_difficultyBeatmapSets[{_beatmapCharacteristicName:"Standard", _difficultyBeatmaps[{_difficulty,_difficultyRank,_beatmapFilename,_noteJumpMovementSpeed,_noteJumpStartBeatOffset}]}]`.
2. v4: `song{title,subTitle,author}`, `audio{songFilename,bpm,previewStartTime,previewDuration}`, `coverImageFilename`, `environmentNames[]`, `colorSchemes[]`, and `difficultyBeatmaps[{characteristic,difficulty,beatmapAuthors{mappers},environmentNameIdx,beatmapColorSchemeIdx,noteJumpMovementSpeed,noteJumpStartBeatOffset,beatmapDataFilename,lightshowDataFilename}]`.

## Tempo regions

1. v4 keeps tempo in the audio-data file named by Info `audio.audioDataFilename` (commonly `AudioData.dat`): `songFrequency` and `bpmData[{si,ei,sb,eb}]` (start and end sample index, start and end beat).
2. Legacy v2 and v3 maps may have `BPMInfo.dat`: `_songFrequency` and `_regions[{_startSampleIndex,_endSampleIndex,_startBeat,_endBeat}]`. It is used only for a difficulty with no tempo events of its own.
3. Regions are joined into one sample-to-beat piecewise-linear map. A first region at `si > 0` and `sb > 0` gets a prepended `(0,0)->(si,sb)` segment; a gap between regions is filled by the joining segment (a gap of at most 2 samples with no beat gap is ignored). Each segment becomes a tempo event at its start beat with `bpm = (eb - sb) / ((ei - si) / songFrequency) * 60`. Zero-length regions are skipped. After merging with difficulty events, an event within 0.01% of the previous tempo (the Info bpm for the first) is dropped.
4. For v4, region events merge into every difficulty; a difficulty event at the same beat wins.
5. A missing file gives no events. The filename goes through the plain-filename check. Bad numbers, reversed ranges or a non-positive frequency raise `MapParseError`. Unsupported: audio lead-in before beat 0 (`si > 0`, `sb = 0`), overlapping regions, a gap with only one axis advancing, and a region with one empty axis; all raise `MapParseError`.
6. The writer emits the events as v3 `bpmEvents`.

## Writer output

1. Info `_version` is `"2.1.0"`.
2. `_environmentName` is the environment of the map and `_environmentNames` is `[environment]`.
3. When a colour scheme is set, `_colorSchemes` is `[{"useOverride": true, "colorScheme": {"colorSchemeId": id, ...colors}}]`, and each difficulty gets `_environmentNameIdx: 0` and `_beatmapColorSchemeIdx: 0`.
4. Each difficulty is written as `<Name>.dat` with this v3.3.0 shape: `version "3.3.0"`, `bpmEvents`, `rotationEvents: []`, `colorNotes`, `bombNotes`, `obstacles`, `sliders`, `burstSliders`, `waypoints: []`, `basicBeatmapEvents`, `colorBoostBeatmapEvents`, `lightColorEventBoxGroups`, `lightRotationEventBoxGroups`, `lightTranslationEventBoxGroups`, `vfxEventBoxGroups`, `_fxEventsCollection` (copied from the source when present, and then `vfxEventBoxGroups` are kept; otherwise `{"_fl": [], "_il": []}` and no vfx groups), `basicEventTypesWithKeywords: {"d": []}`, `useNormalEventsAsCompatibleEvents: true`.
5. Box-group and slider lists come from the preserved raw difficulty data, and are empty lists when absent.
6. No `customData` keys are written.
