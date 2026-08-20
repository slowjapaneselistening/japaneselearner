(function () {
    'use strict';

    if (window.__slowjpPlaybackControlsLoaded) return;
    window.__slowjpPlaybackControlsLoaded = true;

    const SUPPORTED_RATES = [0.85, 1, 1.15, 1.25];
    let playbackRate = 0.85;
    let playbackRunId = 0;
    let isPaused = false;
    let activeLineIndex = 0;
    let pausedAudio = null;

    function clearHighlights() {
        document.querySelectorAll('.message-bubble').forEach(bubble => {
            bubble.classList.remove('ring-2', 'ring-blue-400', 'ring-purple-400');
        });
    }

    function setPlayButtonState(isPlaying) {
        const button = document.getElementById('play-scene-btn');
        if (!button) return;
        button.innerHTML = isPlaying
            ? '<i class="fa-solid fa-pause"></i> Pause'
            : '<i class="fa-solid fa-play"></i> Play';
    }

    function releaseCurrentAudio(preserveAudio) {
        if (typeof currentAudio !== 'undefined' && currentAudio) {
            const audio = currentAudio;
            const finish = audio.onended;
            audio.onended = null;
            audio.onerror = null;
            audio.pause();
            if (typeof finish === 'function') finish();
            if (!preserveAudio) currentAudio = null;
        }
    }

    function pausePlayback() {
        playbackRunId++;
        pausedAudio = (typeof currentAudio !== 'undefined' && currentAudio && !currentAudio.ended)
            ? currentAudio
            : null;
        releaseCurrentAudio(true);
        isPaused = true;
        appState.isPlaying = false;
        setPlayButtonState(false);
    }

    function stopPlayback() {
        playbackRunId++;
        releaseCurrentAudio(false);
        isPaused = false;
        pausedAudio = null;
        activeLineIndex = 0;
        if (typeof appState !== 'undefined') appState.isPlaying = false;
        setPlayButtonState(false);
        clearHighlights();
    }

    function setPlaybackRate(value) {
        const rate = Number(value);
        if (!SUPPORTED_RATES.includes(rate)) return;
        playbackRate = rate;
        window.slowjpPlaybackRate = rate;
        if (typeof currentAudio !== 'undefined' && currentAudio) {
            currentAudio.playbackRate = rate;
        }
    }

    async function playSceneFrom(startIndex, forceRestart) {
        if (typeof appState === 'undefined' || typeof scenes === 'undefined') return;

        if (appState.isPlaying && !forceRestart) {
            pausePlayback();
            return;
        }

        const shouldResume = isPaused && !forceRestart;
        const resumeAudio = shouldResume ? pausedAudio : null;
        const requestedStart = shouldResume ? activeLineIndex : startIndex;

        if (!shouldResume) stopPlayback();
        isPaused = false;
        pausedAudio = null;
        const runId = playbackRunId;
        appState.isPlaying = true;
        setPlayButtonState(true);

        const scene = scenes[appState.currentSceneIndex];
        const firstLine = Math.max(0, Math.min(Number(requestedStart) || 0, scene.lines.length - 1));

        for (let i = firstLine; i < scene.lines.length; i++) {
            if (!appState.isPlaying || runId !== playbackRunId) return;

            activeLineIndex = i;
            const line = scene.lines[i];
            const isMuted = appState.roleplayMutedSpeaker === line.speaker;
            const bubbles = document.querySelectorAll('.message-bubble');
            clearHighlights();

            if (bubbles[i]) {
                bubbles[i].classList.add('ring-2', isMuted ? 'ring-purple-400' : 'ring-blue-400');
                bubbles[i].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            if (isMuted) {
                await new Promise(resolve => setTimeout(resolve, 1500 + line.speakText.length * 150));
            } else if (line.audioPath) {
                await new Promise(resolve => {
                    if (currentAudio) currentAudio.pause();
                    currentAudio = (i === firstLine && resumeAudio) ? resumeAudio : new Audio(line.audioPath);
                    currentAudio.playbackRate = playbackRate;
                    currentAudio.onended = resolve;
                    currentAudio.onerror = resolve;
                    currentAudio.play().catch(error => {
                        console.error('Audio play failed in loop:', error);
                        resolve();
                    });
                });
            } else {
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

            if (!appState.isPlaying || runId !== playbackRunId) return;
            await new Promise(resolve => setTimeout(resolve, 600));
        }

        if (runId === playbackRunId) stopPlayback();
    }

    function installRateSelector() {
        const roleplaySelector = document.getElementById('roleplay-selector');
        if (!roleplaySelector || document.getElementById('playback-rate-selector')) return;

        const selector = document.createElement('select');
        selector.id = 'playback-rate-selector';
        selector.className = 'bg-white border border-gray-300 text-gray-800 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2 font-medium shadow-sm';
        selector.title = 'Playback speed';
        selector.setAttribute('aria-label', 'Playback speed');
        selector.innerHTML = SUPPORTED_RATES.map(rate => `<option value="${rate}">${rate}×</option>`).join('');
        selector.value = String(playbackRate);
        selector.addEventListener('change', event => setPlaybackRate(event.target.value));
        roleplaySelector.insertAdjacentElement('afterend', selector);
    }

    function installDialogueStartPlayback() {
        const dialogueList = document.getElementById('dialogue-list');
        if (!dialogueList || dialogueList.dataset.startPlaybackEnabled === 'true') return;

        dialogueList.dataset.startPlaybackEnabled = 'true';
        dialogueList.addEventListener('click', event => {
            if (event.target.closest('button, a, input, select, .kanji-hidden')) return;
            const bubble = event.target.closest('.message-bubble');
            if (!bubble) return;
            const bubbles = Array.from(dialogueList.querySelectorAll('.message-bubble'));
            const lineIndex = bubbles.indexOf(bubble);
            if (lineIndex >= 0) playSceneFrom(lineIndex, true);
        });

        const markBubblesClickable = () => {
            dialogueList.querySelectorAll('.message-bubble').forEach((bubble, index) => {
                bubble.classList.add('cursor-pointer', 'hover:ring-2', 'hover:ring-blue-200');
                bubble.title = `Start playing from line ${index + 1}`;
                bubble.setAttribute('role', 'button');
                bubble.setAttribute('tabindex', '0');
            });
        };

        dialogueList.addEventListener('keydown', event => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            const bubble = event.target.closest('.message-bubble');
            if (!bubble) return;
            event.preventDefault();
            const bubbles = Array.from(dialogueList.querySelectorAll('.message-bubble'));
            playSceneFrom(bubbles.indexOf(bubble), true);
        });

        new MutationObserver(markBubblesClickable).observe(dialogueList, { childList: true, subtree: true });
        markBubblesClickable();
    }

    const originalPlayAudio = window.playAudio;
    if (typeof originalPlayAudio === 'function') {
        window.playAudio = function (audioPath) {
            originalPlayAudio(audioPath);
            if (typeof currentAudio !== 'undefined' && currentAudio) currentAudio.playbackRate = playbackRate;
        };
    }

    window.slowjpPlaybackRate = playbackRate;
    window.setPlaybackRate = setPlaybackRate;
    window.playEntireScene = function (startIndex = 0, forceRestart = false) {
        return playSceneFrom(startIndex, forceRestart);
    };
    window.playSceneFrom = function (startIndex) {
        return playSceneFrom(startIndex, true);
    };

    function init() {
        installRateSelector();
        installDialogueStartPlayback();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
