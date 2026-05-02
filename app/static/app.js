(() => {
  const cards = Array.from(document.querySelectorAll(".animal-card"));
  const liveStatus = document.getElementById("sound-status");
  let audioContext = null;

  function getAudioContext() {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
      throw new Error("Web Audio is not supported in this browser.");
    }

    if (!audioContext) {
      audioContext = new AudioContextClass();
    }

    return audioContext;
  }

  function createGain(context, start, duration, peak = 0.25, attack = 0.025, release = 0.08) {
    const gain = context.createGain();
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(peak, start + attack);
    gain.gain.setValueAtTime(peak, Math.max(start + attack, start + duration - release));
    gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    return gain;
  }

  function tone(context, start, duration, fromFrequency, toFrequency, options = {}) {
    const oscillator = context.createOscillator();
    const gain = createGain(
      context,
      start,
      duration,
      options.gain ?? 0.22,
      options.attack ?? 0.025,
      options.release ?? 0.08,
    );

    oscillator.type = options.type || "sine";
    oscillator.frequency.setValueAtTime(fromFrequency, start);
    oscillator.frequency.exponentialRampToValueAtTime(Math.max(1, toFrequency), start + duration * 0.85);

    if (options.filterFrequency) {
      const filter = context.createBiquadFilter();
      filter.type = options.filterType || "lowpass";
      filter.frequency.setValueAtTime(options.filterFrequency, start);
      oscillator.connect(filter);
      filter.connect(gain);
    } else {
      oscillator.connect(gain);
    }

    gain.connect(context.destination);
    oscillator.start(start);
    oscillator.stop(start + duration + 0.03);
  }

  function noise(context, start, duration, options = {}) {
    const sampleCount = Math.max(1, Math.floor(context.sampleRate * duration));
    const buffer = context.createBuffer(1, sampleCount, context.sampleRate);
    const channel = buffer.getChannelData(0);

    for (let index = 0; index < sampleCount; index += 1) {
      channel[index] = Math.random() * 2 - 1;
    }

    const source = context.createBufferSource();
    const filter = context.createBiquadFilter();
    const gain = createGain(
      context,
      start,
      duration,
      options.gain ?? 0.08,
      options.attack ?? 0.01,
      options.release ?? 0.03,
    );

    source.buffer = buffer;
    filter.type = options.filterType || "bandpass";
    filter.frequency.setValueAtTime(options.frequency ?? 700, start);
    filter.Q.setValueAtTime(options.q ?? 1.8, start);

    source.connect(filter);
    filter.connect(gain);
    gain.connect(context.destination);
    source.start(start);
    source.stop(start + duration);
  }

  const soundPatterns = {
    moo(context, start) {
      tone(context, start, 0.82, 165, 92, { gain: 0.32, type: "sine", filterFrequency: 420 });
      tone(context, start + 0.12, 0.7, 125, 82, { gain: 0.18, type: "triangle", filterFrequency: 360 });
      return 950;
    },

    neigh(context, start) {
      tone(context, start, 0.14, 520, 760, { gain: 0.18, type: "sawtooth", filterFrequency: 1600 });
      tone(context, start + 0.14, 0.16, 760, 560, { gain: 0.2, type: "sawtooth", filterFrequency: 1500 });
      tone(context, start + 0.3, 0.18, 640, 420, { gain: 0.18, type: "triangle", filterFrequency: 1300 });
      noise(context, start + 0.06, 0.22, { gain: 0.035, frequency: 1400, q: 2.5 });
      return 640;
    },

    baa(context, start) {
      tone(context, start, 0.32, 390, 265, { gain: 0.2, type: "triangle", filterFrequency: 900 });
      tone(context, start + 0.28, 0.38, 335, 215, { gain: 0.24, type: "triangle", filterFrequency: 780 });
      tone(context, start + 0.45, 0.2, 280, 230, { gain: 0.11, type: "sine", filterFrequency: 650 });
      return 820;
    },

    oink(context, start) {
      noise(context, start, 0.08, { gain: 0.12, frequency: 540, q: 4 });
      tone(context, start + 0.03, 0.16, 210, 145, { gain: 0.18, type: "square", filterFrequency: 480 });
      noise(context, start + 0.22, 0.08, { gain: 0.11, frequency: 620, q: 4 });
      tone(context, start + 0.25, 0.15, 240, 150, { gain: 0.16, type: "square", filterFrequency: 500 });
      return 560;
    },

    cluck(context, start) {
      for (let index = 0; index < 4; index += 1) {
        const offset = index * 0.12;
        tone(context, start + offset, 0.055, 820 - index * 70, 430, {
          gain: 0.12,
          type: "triangle",
          attack: 0.006,
          release: 0.025,
          filterFrequency: 1400,
        });
        noise(context, start + offset, 0.04, { gain: 0.045, frequency: 950, q: 3.5 });
      }
      return 620;
    },

    quack(context, start) {
      tone(context, start, 0.18, 265, 175, { gain: 0.24, type: "square", filterFrequency: 620 });
      noise(context, start, 0.16, { gain: 0.05, frequency: 520, q: 3 });
      tone(context, start + 0.26, 0.2, 250, 168, { gain: 0.22, type: "square", filterFrequency: 590 });
      noise(context, start + 0.26, 0.15, { gain: 0.045, frequency: 500, q: 3 });
      return 620;
    },

    bleat(context, start) {
      tone(context, start, 0.16, 470, 365, { gain: 0.2, type: "triangle", filterFrequency: 980 });
      tone(context, start + 0.15, 0.2, 520, 310, { gain: 0.23, type: "triangle", filterFrequency: 900 });
      tone(context, start + 0.34, 0.22, 455, 275, { gain: 0.18, type: "triangle", filterFrequency: 820 });
      return 700;
    },

    "hee-haw"(context, start) {
      tone(context, start, 0.34, 430, 320, { gain: 0.24, type: "sawtooth", filterFrequency: 900 });
      tone(context, start + 0.38, 0.48, 190, 105, { gain: 0.3, type: "sine", filterFrequency: 420 });
      noise(context, start + 0.34, 0.22, { gain: 0.035, frequency: 620, q: 2.2 });
      return 1050;
    },
  };

  async function playAnimal(card) {
    const patternName = card.dataset.soundPattern;
    const pattern = soundPatterns[patternName];
    const animalName = card.dataset.animalName;
    const soundLabel = card.dataset.soundLabel;

    if (!pattern) {
      return;
    }

    const context = getAudioContext();
    if (context.state === "suspended") {
      await context.resume();
    }

    const duration = pattern(context, context.currentTime + 0.03);

    card.classList.add("is-playing");
    window.setTimeout(() => card.classList.remove("is-playing"), duration);

    if (liveStatus) {
      liveStatus.textContent = `${animalName} says ${soundLabel}.`;
    }
  }

  function activateCard(event) {
    playAnimal(event.currentTarget).catch(() => {
      if (liveStatus) {
        liveStatus.textContent = "Sound is unavailable in this browser.";
      }
    });
  }

  cards.forEach((card) => {
    card.addEventListener("click", activateCard);
    card.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }

      event.preventDefault();
      activateCard(event);
    });
  });
})();
