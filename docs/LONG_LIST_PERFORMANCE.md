# Long lists and chat

The modern library formerly created every card with `Repeater`. With 1,000 results,
all 1,000 cards and roughly 47,000 visual nodes existed, including text, input handlers,
image/effect objects and bindings. Clipping and stopping offscreen artwork did not remove
those objects. The scene still had to traverse them and propagate changes during scrolling.

The library and instances now use a bounded `GridView`; installed content, server results,
mod repair, imports, friends and chat use bounded `ListView` delegates. Cosmetic choices
and mod sharing lists use the same inertia controller. `reuseItems` and a small cache
preserve responsive scrolling. Installed rows retain their existing keyed model so toggling
or updating one mod does not reset the list. Confirmation state resets when a row is reused.

Card artwork captures are static and use 160px sources; they refresh after an image changes
or becomes ready. Rounded masks refresh on resize instead of capturing continuously. Live
popup backgrounds retain their blur. Hidden/unfrosted glass disconnects capture sources.

A local Qt/Xorg run using software OpenGL, at 1440×900, compared 100 and 1,000 results:

| Results | Before: project cards / visual nodes | After: project cards / visual nodes |
| --- | --- | --- |
| 100 | 100 / 5,548 | 9 / 1,369 |
| 1,000 | 1,000 / 46,948 | 9 / 1,369 |

These are measurements for this viewport and test fixture, not guaranteed frame rates
on another computer. Regression tests exercise 2,000 projects and installed files, reach
the last row, return to the top, and check delegate bounds, recycled state and scroll
position when a mod changes.

Chat previously shared the account polling worker's `busy` flag. Sending now has a separate
worker and only waits for another send. Offline accepted friends can receive messages.
Pending requests and blocked accounts still cannot chat. Unchanged account snapshots do
not rebuild social models; revoked sessions discard stale delivery results.
