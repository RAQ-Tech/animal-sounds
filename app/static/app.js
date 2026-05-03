(() => {
  const cards = Array.from(document.querySelectorAll(".animal-card"));
  const sourceButtons = Array.from(document.querySelectorAll("[data-sound-source]"));
  const throwToggle = document.getElementById("throw-mode-toggle");
  const throwLayer = document.getElementById("pokeball-layer");
  const liveStatus = document.getElementById("sound-status");
  const SOUND_SOURCE_STORAGE_KEY = "animal-sounds-source";
  let audioContext = null;
  let throwModeActive = false;
  let throwAnimationTimer = null;
  let soundSourceMode = "generated";
  let localAudioByAnimal = {};
  let localAudioIndexes = {};
  let currentLocalAudio = null;

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

  function setLiveStatus(message) {
    if (liveStatus) {
      liveStatus.textContent = message;
    }
  }

  function isActivationKey(event) {
    return event.key === "Enter" || event.key === " " || event.key === "Space" || event.key === "Spacebar";
  }

  function getStoredSoundSourceMode() {
    try {
      const storedMode = window.localStorage.getItem(SOUND_SOURCE_STORAGE_KEY);
      return storedMode === "local" ? "local" : "generated";
    } catch {
      return "generated";
    }
  }

  function storeSoundSourceMode(mode) {
    try {
      window.localStorage.setItem(SOUND_SOURCE_STORAGE_KEY, mode);
    } catch {
      // localStorage can be unavailable in hardened browser contexts.
    }
  }

  function updateSourceButtons() {
    sourceButtons.forEach((button) => {
      const isSelected = button.dataset.soundSource === soundSourceMode;
      button.classList.toggle("is-selected", isSelected);
      button.setAttribute("aria-pressed", isSelected ? "true" : "false");
    });
  }

  function setSoundSourceMode(mode, options = {}) {
    soundSourceMode = mode === "local" ? "local" : "generated";
    updateSourceButtons();

    if (options.persist !== false) {
      storeSoundSourceMode(soundSourceMode);
    }

    if (options.announce !== false) {
      setLiveStatus(
        soundSourceMode === "local"
          ? "Local Files mode on. Animal clicks use files from config when available."
          : "Generated sounds mode on.",
      );
    }
  }

  function localAudioFilesFor(card) {
    const animalAudio = localAudioByAnimal[card.dataset.animalId];
    if (!animalAudio || !Array.isArray(animalAudio.files)) {
      return [];
    }
    return animalAudio.files;
  }

  function updateLocalAudioCardState() {
    cards.forEach((card) => {
      const fileCount = localAudioFilesFor(card).length;
      card.dataset.localAudioCount = String(fileCount);
      card.classList.toggle("has-local-audio", fileCount > 0);
    });
  }

  async function refreshLocalAudioIndex() {
    try {
      const response = await fetch("/api/audio", {
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Audio index failed with ${response.status}`);
      }

      const payload = await response.json();
      localAudioByAnimal = payload.animals || {};
      updateLocalAudioCardState();
    } catch {
      localAudioByAnimal = {};
      updateLocalAudioCardState();
      if (soundSourceMode === "local") {
        setLiveStatus("Local audio files are unavailable; generated sounds will play.");
      }
    }
  }

  function setThrowMode(active) {
    throwModeActive = active;

    if (throwToggle) {
      throwToggle.classList.toggle("is-armed", active);
      throwToggle.setAttribute("aria-pressed", active ? "true" : "false");
    }

    setLiveStatus(
      active
        ? "Throw mode ready. Choose an animal to throw a Pokeball."
        : "Throw mode off. Animal cards play sounds.",
    );
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

    bark(context, start) {
      tone(context, start, 0.12, 210, 125, { gain: 0.28, type: "square", filterFrequency: 720 });
      noise(context, start, 0.09, { gain: 0.085, frequency: 820, q: 3.6 });
      tone(context, start + 0.22, 0.13, 240, 135, { gain: 0.26, type: "square", filterFrequency: 760 });
      noise(context, start + 0.22, 0.09, { gain: 0.08, frequency: 900, q: 3.4 });
      return 520;
    },

    meow(context, start) {
      tone(context, start, 0.34, 520, 820, { gain: 0.16, type: "sine", filterFrequency: 1500 });
      tone(context, start + 0.28, 0.44, 820, 420, { gain: 0.2, type: "triangle", filterFrequency: 1300 });
      tone(context, start + 0.18, 0.38, 620, 520, { gain: 0.06, type: "sine", filterFrequency: 1100 });
      return 880;
    },

    roar(context, start) {
      noise(context, start, 0.82, { gain: 0.16, frequency: 260, q: 1.4 });
      tone(context, start, 0.9, 145, 72, { gain: 0.3, type: "sawtooth", filterFrequency: 430 });
      tone(context, start + 0.18, 0.64, 95, 58, { gain: 0.18, type: "triangle", filterFrequency: 360 });
      return 1080;
    },

    chatter(context, start) {
      for (let index = 0; index < 7; index += 1) {
        const offset = index * 0.08;
        tone(context, start + offset, 0.045, 740 + index * 24, 530, {
          gain: 0.1,
          type: "square",
          attack: 0.004,
          release: 0.018,
          filterFrequency: 1700,
        });
      }
      noise(context, start + 0.02, 0.48, { gain: 0.025, frequency: 1200, q: 2.8 });
      return 700;
    },

    "gorilla-grunt"(context, start) {
      tone(context, start, 0.24, 125, 86, { gain: 0.28, type: "sine", filterFrequency: 330 });
      noise(context, start + 0.02, 0.22, { gain: 0.06, frequency: 280, q: 1.8 });
      tone(context, start + 0.34, 0.26, 118, 78, { gain: 0.26, type: "triangle", filterFrequency: 300 });
      noise(context, start + 0.36, 0.2, { gain: 0.055, frequency: 260, q: 1.7 });
      return 780;
    },

    "tiger-growl"(context, start) {
      noise(context, start, 0.68, { gain: 0.14, frequency: 210, q: 1.5 });
      tone(context, start, 0.76, 120, 68, { gain: 0.28, type: "sawtooth", filterFrequency: 380 });
      tone(context, start + 0.28, 0.34, 92, 62, { gain: 0.16, type: "square", filterFrequency: 330 });
      return 920;
    },

    "dolphin-click"(context, start) {
      for (let index = 0; index < 5; index += 1) {
        const offset = index * 0.075;
        tone(context, start + offset, 0.026, 2200 + index * 180, 1250, {
          gain: 0.095,
          type: "square",
          attack: 0.003,
          release: 0.012,
          filterFrequency: 2800,
        });
      }
      tone(context, start + 0.4, 0.18, 1650, 2400, { gain: 0.07, type: "sine", filterFrequency: 3200 });
      return 680;
    },

    "elephant-trumpet"(context, start) {
      tone(context, start, 0.28, 280, 690, { gain: 0.22, type: "sawtooth", filterFrequency: 1400 });
      tone(context, start + 0.2, 0.42, 690, 230, { gain: 0.25, type: "sawtooth", filterFrequency: 1200 });
      noise(context, start + 0.04, 0.52, { gain: 0.045, frequency: 950, q: 2.4 });
      return 820;
    },

    "cricket-chirp"(context, start) {
      for (let group = 0; group < 3; group += 1) {
        for (let index = 0; index < 3; index += 1) {
          const offset = group * 0.19 + index * 0.038;
          tone(context, start + offset, 0.026, 3150, 2600, {
            gain: 0.06,
            type: "square",
            attack: 0.002,
            release: 0.01,
            filterFrequency: 3600,
          });
        }
      }
      return 760;
    },

    "coyote-howl"(context, start) {
      tone(context, start, 0.38, 270, 430, { gain: 0.16, type: "sine", filterFrequency: 900 });
      tone(context, start + 0.32, 0.72, 430, 190, { gain: 0.24, type: "triangle", filterFrequency: 780 });
      noise(context, start + 0.58, 0.26, { gain: 0.025, frequency: 760, q: 2.1 });
      return 1220;
    },

    "rooster-crow"(context, start) {
      tone(context, start, 0.16, 570, 840, { gain: 0.17, type: "sawtooth", filterFrequency: 1600 });
      tone(context, start + 0.16, 0.22, 840, 620, { gain: 0.22, type: "sawtooth", filterFrequency: 1500 });
      tone(context, start + 0.42, 0.36, 720, 390, { gain: 0.24, type: "triangle", filterFrequency: 1250 });
      noise(context, start + 0.12, 0.26, { gain: 0.03, frequency: 1350, q: 2.5 });
      return 980;
    },

    "frog-croak"(context, start) {
      tone(context, start, 0.22, 170, 118, { gain: 0.24, type: "square", filterFrequency: 420 });
      noise(context, start, 0.18, { gain: 0.055, frequency: 300, q: 1.8 });
      tone(context, start + 0.32, 0.3, 150, 95, { gain: 0.28, type: "square", filterFrequency: 360 });
      noise(context, start + 0.32, 0.24, { gain: 0.06, frequency: 280, q: 1.7 });
      return 820;
    },

    "owl-hoot"(context, start) {
      tone(context, start, 0.34, 310, 210, { gain: 0.2, type: "sine", filterFrequency: 720 });
      tone(context, start + 0.11, 0.24, 235, 190, { gain: 0.13, type: "triangle", filterFrequency: 560 });
      tone(context, start + 0.48, 0.44, 280, 170, { gain: 0.24, type: "sine", filterFrequency: 660 });
      tone(context, start + 0.64, 0.25, 210, 150, { gain: 0.12, type: "triangle", filterFrequency: 520 });
      return 1120;
    },

    "seal-bark"(context, start) {
      tone(context, start, 0.12, 360, 185, { gain: 0.24, type: "square", filterFrequency: 900 });
      noise(context, start, 0.08, { gain: 0.07, frequency: 980, q: 3.3 });
      tone(context, start + 0.2, 0.12, 420, 220, { gain: 0.22, type: "square", filterFrequency: 980 });
      noise(context, start + 0.2, 0.08, { gain: 0.065, frequency: 1100, q: 3.1 });
      tone(context, start + 0.39, 0.12, 380, 190, { gain: 0.18, type: "square", filterFrequency: 920 });
      return 660;
    },
  };

  function stopCurrentLocalAudio() {
    if (!currentLocalAudio) {
      return;
    }

    currentLocalAudio.pause();
    currentLocalAudio.currentTime = 0;
    currentLocalAudio = null;
  }

  async function playGeneratedAnimal(card, statusMessage = null) {
    const patternName = card.dataset.soundPattern;
    const pattern = soundPatterns[patternName];
    const animalName = card.dataset.animalName;
    const soundLabel = card.dataset.soundLabel;

    if (!pattern) {
      return;
    }

    stopCurrentLocalAudio();

    const context = getAudioContext();
    if (context.state === "suspended") {
      await context.resume();
    }

    const duration = pattern(context, context.currentTime + 0.03);

    card.classList.add("is-playing");
    window.setTimeout(() => card.classList.remove("is-playing"), duration);

    setLiveStatus(statusMessage || `${animalName} says ${soundLabel}.`);
  }

  async function playLocalAnimal(card, files) {
    const animalId = card.dataset.animalId;
    const animalName = card.dataset.animalName;
    const nextIndex = localAudioIndexes[animalId] || 0;
    const file = files[nextIndex % files.length];
    const audio = new Audio(file.url);

    localAudioIndexes = {
      ...localAudioIndexes,
      [animalId]: nextIndex + 1,
    };

    stopCurrentLocalAudio();
    currentLocalAudio = audio;
    audio.preload = "auto";

    card.classList.add("is-playing");
    audio.addEventListener(
      "ended",
      () => {
        if (currentLocalAudio === audio) {
          currentLocalAudio = null;
          card.classList.remove("is-playing");
        }
      },
      { once: true },
    );
    audio.addEventListener(
      "error",
      () => {
        if (currentLocalAudio === audio) {
          currentLocalAudio = null;
          card.classList.remove("is-playing");
          setLiveStatus(`Local audio file could not play for ${animalName}.`);
        }
      },
      { once: true },
    );

    await audio.play();
    setLiveStatus(`Playing local file ${file.name} for ${animalName}.`);
  }

  async function playAnimal(card) {
    const animalName = card.dataset.animalName;
    const soundLabel = card.dataset.soundLabel;
    let generatedStatusMessage = null;

    if (soundSourceMode === "local") {
      const localFiles = localAudioFilesFor(card);

      if (localFiles.length > 0) {
        try {
          await playLocalAnimal(card, localFiles);
          return;
        } catch {
          card.classList.remove("is-playing");
          generatedStatusMessage = `Local audio failed for ${animalName}; playing generated ${soundLabel}.`;
        }
      } else {
        generatedStatusMessage = `No local audio files for ${animalName}; playing generated ${soundLabel}.`;
      }
    }

    await playGeneratedAnimal(card, generatedStatusMessage);
  }

  function clearThrowAnimation() {
    if (throwAnimationTimer) {
      window.clearTimeout(throwAnimationTimer);
      throwAnimationTimer = null;
    }

    if (throwLayer) {
      throwLayer.replaceChildren();
    }
  }

  function createPokeball() {
    const ball = document.createElement("span");
    ball.className = "pokeball";
    ball.innerHTML = '<span class="pokeball-center"></span>';
    return ball;
  }

  function throwPokeball(targetCard) {
    if (!throwLayer || !throwToggle) {
      return;
    }

    clearThrowAnimation();

    const throwRect = throwToggle.getBoundingClientRect();
    const targetRect = targetCard.getBoundingClientRect();
    const startX = throwRect.left + throwRect.width / 2;
    const startY = throwRect.top + throwRect.height / 2;
    const endX = targetRect.left + targetRect.width / 2;
    const endY = targetRect.top + Math.max(48, targetRect.height * 0.42);
    const arcY = Math.min(startY, endY) - 110;
    const animalName = targetCard.dataset.animalName;
    const ball = createPokeball();

    ball.style.setProperty("--start-x", `${startX}px`);
    ball.style.setProperty("--start-y", `${startY}px`);
    ball.style.setProperty("--arc-x", `${(startX + endX) / 2}px`);
    ball.style.setProperty("--arc-y", `${arcY}px`);
    ball.style.setProperty("--end-x", `${endX}px`);
    ball.style.setProperty("--end-y", `${endY}px`);

    throwLayer.append(ball);
    targetCard.classList.add("is-pokeball-target");
    setLiveStatus(`Pokeball thrown at ${animalName}.`);

    throwAnimationTimer = window.setTimeout(() => {
      targetCard.classList.remove("is-pokeball-target");
      clearThrowAnimation();
      setLiveStatus(`Pokeball bounced off ${animalName}.`);
    }, 960);
  }

  function activateCard(event) {
    const card = event.currentTarget;
    const shouldThrow = throwModeActive;

    playAnimal(card)
      .then(() => {
        if (!shouldThrow) {
          return;
        }

        setThrowMode(false);
        throwPokeball(card);
      })
      .catch(() => {
        setLiveStatus("Sound is unavailable in this browser.");
        if (shouldThrow) {
          setThrowMode(false);
        }
      });
  }

  sourceButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setSoundSourceMode(button.dataset.soundSource);
    });

    button.addEventListener("keydown", (event) => {
      if (!isActivationKey(event)) {
        return;
      }

      event.preventDefault();
      setSoundSourceMode(button.dataset.soundSource);
    });
  });

  if (throwToggle) {
    throwToggle.addEventListener("click", () => {
      setThrowMode(!throwModeActive);
    });

    throwToggle.addEventListener("keydown", (event) => {
      if (isActivationKey(event)) {
        event.preventDefault();
        setThrowMode(!throwModeActive);
        return;
      }

      if (event.key === "Escape") {
        event.preventDefault();
        setThrowMode(false);
      }
    });
  }

  cards.forEach((card) => {
    card.addEventListener("click", activateCard);
    card.addEventListener("keydown", (event) => {
      if (!isActivationKey(event)) {
        return;
      }

      event.preventDefault();
      activateCard(event);
    });
  });

  setSoundSourceMode(getStoredSoundSourceMode(), { persist: false, announce: false });
  refreshLocalAudioIndex();
})();
