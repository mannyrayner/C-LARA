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
  const svgWords = contextDocument.querySelectorAll('.svg-word');
  const speakerIcons = contextDocument.querySelectorAll('.speaker-icon');
  const translationIcons = contextDocument.querySelectorAll('.translation-icon');
  
  words.forEach(setUpWordEventListener);
  svgWords.forEach(setUpWordEventListener);
  speakerIcons.forEach(setUpSpeakerIconEventListener);
  translationIcons.forEach(setUpTranslationIconEventListener);
  
  function setUpWordEventListener(word) {
    word.addEventListener('click', async () => {
      const audioSrc = word.getAttribute('data-audio');
	  console.log("Playing word audio file: " + audioSrc);
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
	  
      const mweId = word.getAttribute('data-mwe-id');
      if (mweId) {
        highlightMwe(mweId, contextDocument);
      }
	});
	  
	// Hover event for highlighting MWEs
    word.addEventListener('mouseover', () => {
        const mweId = word.getAttribute('data-mwe-id');
        if (mweId) {
            const allWordsInMwe = document.querySelectorAll(`[data-mwe-id="${mweId}"]`);
            allWordsInMwe.forEach(wordInMwe => wordInMwe.classList.add('mwe-group-hover'));
        }
    });

    word.addEventListener('mouseout', () => {
        const mweId = word.getAttribute('data-mwe-id');
        if (mweId) {
            const allWordsInMwe = document.querySelectorAll(`[data-mwe-id="${mweId}"]`);
            allWordsInMwe.forEach(wordInMwe => wordInMwe.classList.remove('mwe-group-hover'));
        }
    });
  }

  function setUpSpeakerIconEventListener(icon) {
    icon.addEventListener('click', () => {
      const segment = icon.parentElement;
      const audioSrc = segment.getAttribute('data-segment-audio');
      if (audioSrc) {
        const audio = new Audio(audioSrc);
        audio.play();
      }
    });
  };
  
  function setUpTranslationIconEventListener(icon) {
    icon.addEventListener('click', () => {
        const translationText = icon.getAttribute('data-translation');
        console.log("Creating translation popup for: " + translationText);
        
        let popup = document.createElement('div');
        popup.classList.add('translation-popup');
        popup.innerText = translationText;

        // Calculate position
        let rect = icon.getBoundingClientRect();
        let top = rect.top + window.scrollY + 20;
        let left = rect.left + window.scrollX;
        
        // Adjust position to ensure the popup is within the viewport
        if (left + popup.offsetWidth > window.innerWidth) {
            left = window.innerWidth - popup.offsetWidth - 10; // Add some padding from the right edge
        }
        if (top + popup.offsetHeight > window.innerHeight) {
            top = window.innerHeight - popup.offsetHeight - 10; // Add some padding from the bottom edge
        }

        popup.style.top = top + 'px';
        popup.style.left = left + 'px';
		popup.style.display = 'block'; // Ensure the popup is visible

        // Add the popup to the document
        document.body.appendChild(popup);

        // Remove the popup when clicking outside
        document.addEventListener('click', function removePopup(event) {
            if (!popup.contains(event.target) && event.target !== icon) {
                popup.remove();
                document.removeEventListener('click', removePopup);
            }
        });
    });
  }

  
}

function highlightMwe(mweId, contextDocument) {
    // First, remove any existing highlights
    contextDocument.querySelectorAll('.mwe-highlight').forEach(element => {
        element.classList.remove('mwe-highlight');
    });

    // Add highlight to all words with the same mwe_id
    const mweElements = contextDocument.querySelectorAll(`[data-mwe-id="${mweId}"]`);
    mweElements.forEach(element => {
        element.classList.add('mwe-highlight');
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

