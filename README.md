## Usage

1) Fill in the fields, press "Fetch"
2) Steam doesn't keep track of when you actually played (or rather doesn't expose this via API), so you have to edit the timeline manually so it makes sense and closely matches your original playtime in total. If you've beaten the original in one go, it's not really needed, just repeat it as it was with an offset. But if you've paused for a week in the middle of your playthrough, you'd have to wait for a week again to resume the syncing. Which is tedious, so this app allows to skip it.
3) After that you'll have a list of achievements in an order and their respective unlock times and you can "Save" them in order to avoid repeating the process above.
4) Now you launch a SAM instance with your target game, and press "Replay" button. Every time you should unlock an achievement there will be a beep and total stats are tracked. When you've run SAM for the same playtime as original and unlocked everything correctly, you'll have a replica of the already beaten game. Every time you need to pause, you "Save" everything before closing the app and the process can be continued.

## TODO
I only needed this for a single game, so it won't be developed. But still.
1) Integrate SAM functionality and make the unlocking process fully automatic instead of listening for beeps.
2) Heatmap with a legend for time ranges in between achievements.
3) Separate data storage models from Qt view models.
4) Get rid of potential invalid states by blocking some inputs during replay. The app may be in an invalid state for other reasons too, there are almost no checks.
5) Get rid of some useless actions, such as iterating all rows every second or double replay data recalculation. Much more practical approach is to keep track of the next possible row to unlock. With previous steps done it should be simple
