function removeClassAfterDuration(element, className, duration) {
  setTimeout(() => {
	element.classList.remove(className);
  }, duration);
}

function scrollToSegmentHandler(segmentUid, pageNumber) {
  // Load the correct page before scrolling and pass the segmentUid as a query parameter
  window.location.href = `page_${pageNumber}.html?segmentUid=${segmentUid}`;
}

document.addEventListener('DOMContentLoaded', () => {
  // Read the segmentUid from the query parameter
  const urlParams = new URLSearchParams(window.location.search);
  const segmentUid = urlParams.get('segmentUid');

  if (segmentUid) {
    // If segmentUid is present in the query parameter, scroll to the segment and highlight it
    const targetSegment = document.querySelector(`[data-segment-uid="${segmentUid}"]`);
    if (targetSegment) {
      targetSegment.scrollIntoView();
      targetSegment.classList.add("segment-highlight"); // Add the highlight class
      removeClassAfterDuration(targetSegment, "segment-highlight", 2000); // Remove after 2000 milliseconds
    }
  }
});

function postMessageToParent(type, data) {
  if (window.parent !== window) {
    window.parent.postMessage({ type, data }, "*");
  } else {
    if (type === 'loadConcordance') {
      const concordancePane = document.getElementById("concordance-pane");
      concordancePane.src = `concordance_${data.lemma}.html`;
    } else if (type === 'scrollToSegment') {
      scrollToSegmentHandler(data.segmentUid, data.pageNumber);
    }
  }
}

function setUpEventListeners(contextDocument) {
  console.log("Setting up event listeners");
  const words = contextDocument.querySelectorAll('.word');
  const speakerIcons = contextDocument.querySelectorAll('.speaker-icon');

  words.forEach(word => {
    word.addEventListener('click', async () => {
      const audioSrc = word.getAttribute('data-audio');
      if (audioSrc) {
        const audio = new Audio(audioSrc);
        await new Promise(resolve => {
          audio.onended = resolve;
          audio.onerror = resolve;
          audio.play();
        });
      }

      const lemma = word.getAttribute('data-lemma');
      if (lemma) {
        postMessageToParent('loadConcordance', { lemma });
      }
    });
  });

  speakerIcons.forEach(icon => {
    icon.addEventListener('click', () => {
      const segment = icon.parentElement;
      const audioSrc = segment.getAttribute('data-segment-audio');
      if (audioSrc) {
        const audio = new Audio(audioSrc);
        audio.play();
      }
    });
  });
}

function setUpBackArrowEventListeners(contextDocument) {
  console.log("Setting up back arrow event listeners");
  const backArrowIcons = contextDocument.querySelectorAll('.back-arrow-icon');

  backArrowIcons.forEach(icon => {
    icon.addEventListener('click', () => {
      const segmentUid = icon.getAttribute('data-segment-uid');
      const pageNumber = icon.getAttribute('data-page-number');
      if (segmentUid) {
        postMessageToParent('scrollToSegment', { segmentUid, pageNumber });
      }
    });
  });
}


document.addEventListener('DOMContentLoaded', () => {
  setUpEventListeners(document);
});

/* if (window.frameElement) {
  setUpBackArrowEventListeners(window.frameElement.ownerDocument);
} */

document.addEventListener('DOMContentLoaded', () => {
  setUpBackArrowEventListeners(document);
});

// Event listeners for the vocabulary list buttons

function loadVocabList(url) {
  const concordancePane = document.getElementById("concordance-pane");
  concordancePane.src = url;
}

const vocabFrequencyBtn = document.getElementById("vocab-frequency-btn");
if (vocabFrequencyBtn) {
  vocabFrequencyBtn.addEventListener("click", () => {
    loadVocabList("vocab_list_frequency.html");
  });
}

const vocabAlphabeticalBtn = document.getElementById("vocab-alphabetical-btn");
if (vocabAlphabeticalBtn) {
  vocabAlphabeticalBtn.addEventListener("click", () => {
    loadVocabList("vocab_list_alphabetical.html");
  });
}

