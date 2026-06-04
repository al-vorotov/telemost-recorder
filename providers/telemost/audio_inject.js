/**
 * Захват входящего аудио WebRTC в Телемосте.
 * Python: page.expose_function("onAudioChunk", samples => ...)
 * window.__telemostStartCapture() / __telemostStopCapture()
 */
(function () {
  "use strict";

  let captureActive = false;
  let audioContext = null;
  let processor = null;
  const hookedTracks = new Set();

  function sendChunk(float32Array) {
    if (!captureActive || typeof window.onAudioChunk !== "function") return;
    window.onAudioChunk(Array.from(float32Array));
  }

  function hookAudioTrack(track) {
    if (!track || track.kind !== "audio" || hookedTracks.has(track.id)) return;
    hookedTracks.add(track.id);
    try {
      if (!audioContext) {
        audioContext = new AudioContext();
      }
      const stream = new MediaStream([track]);
      const source = audioContext.createMediaStreamSource(stream);
      if (!processor) {
        processor = audioContext.createScriptProcessor(4096, 1, 1);
        processor.onaudioprocess = function (e) {
          if (!captureActive) return;
          sendChunk(e.inputBuffer.getChannelData(0));
        };
        processor.connect(audioContext.destination);
      }
      source.connect(processor);
    } catch (err) {
      console.warn("[telemost-recorder] hookAudioTrack failed", err);
    }
  }

  function patchPeerConnection(pc) {
    pc.addEventListener("track", function (ev) {
      if (ev.track && ev.track.kind === "audio") hookAudioTrack(ev.track);
    });
    const orig = pc.getReceivers ? pc.getReceivers.bind(pc) : null;
    if (orig) {
      setInterval(function () {
        try {
          pc.getReceivers().forEach(function (r) {
            if (r.track) hookAudioTrack(r.track);
          });
        } catch (_) {}
      }, 3000);
    }
  }

  const OrigPC = window.RTCPeerConnection;
  if (OrigPC) {
    window.RTCPeerConnection = function () {
      const pc = new OrigPC(...arguments);
      patchPeerConnection(pc);
      return pc;
    };
    window.RTCPeerConnection.prototype = OrigPC.prototype;
  }

  window.__telemostStartCapture = function () {
    captureActive = true;
    if (audioContext && audioContext.state === "suspended") {
      audioContext.resume();
    }
  };

  window.__telemostStopCapture = function () {
    captureActive = false;
  };
})();
