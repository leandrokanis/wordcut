import { videoPlayer } from "./videoPlayer";

// The processed video starts at the sermon's start, 1800 s into the live.
const SERMON_START = 1800;

test("seeks the video to the live time minus the sermon's start", () => {
  const element = document.createElement("video");

  videoPlayer(element, SERMON_START).seek(1900);

  expect(element.currentTime).toBe(100);
});

test("tells the video's position as live time", () => {
  const element = document.createElement("video");
  const player = videoPlayer(element, SERMON_START);
  const heard: number[] = [];
  player.onTime((liveSeconds) => heard.push(liveSeconds));

  element.currentTime = 50;
  element.dispatchEvent(new Event("timeupdate"));

  expect([player.time(), ...heard]).toEqual([1850, 1850]);
});
