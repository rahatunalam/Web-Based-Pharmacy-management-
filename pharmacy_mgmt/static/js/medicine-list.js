const searchInput   = document.getElementById('searchInput');
const suggestionsBox = document.getElementById('suggestionsBox');

let debounceTimer = null;
let highlighted = -1;  // tracks keyboard navigation

searchInput.addEventListener('input', () => {
  const query = searchInput.value.trim();

  // Clear any pending timer — we only fetch after user stops typing
  clearTimeout(debounceTimer);

  if (query.length < 1) {
    closeSuggestions();
    return;
  }

  // Wait 250ms after the user stops typing before fetching
  debounceTimer = setTimeout(() => fetchSuggestions(query), 250);
});

async function fetchSuggestions(query) {
  const response = await fetch(
    `/medicine-suggestions/?q=${encodeURIComponent(query)}`
  );
  const data = await response.json();

  if (data.suggestions.length === 0) {
    closeSuggestions();
    return;
  }

  // Build dropdown items
  suggestionsBox.innerHTML = '';
  highlighted = -1;

  data.suggestions.forEach(name => {
    const item = document.createElement('div');
    item.className = 'suggestion-item';
    item.textContent = name;

    // Clicking a suggestion fills the input and submits the form
    item.addEventListener('click', () => {
      searchInput.value = name;
      closeSuggestions();
      searchInput.closest('form').submit();
    });

    suggestionsBox.appendChild(item);
  });

  suggestionsBox.classList.add('is-open');
}

// Keyboard navigation — up/down arrows and Enter
searchInput.addEventListener('keydown', e => {
  const items = suggestionsBox.querySelectorAll('.suggestion-item');

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    highlighted = Math.min(highlighted + 1, items.length - 1);
    updateHighlight(items);

  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    highlighted = Math.max(highlighted - 1, 0);
    updateHighlight(items);

  } else if (e.key === 'Enter' && highlighted >= 0) {
    e.preventDefault();
    searchInput.value = items[highlighted].textContent;
    closeSuggestions();
    searchInput.closest('form').submit();

  } else if (e.key === 'Escape') {
    closeSuggestions();
  }
});

function updateHighlight(items) {
  items.forEach((item, i) => {
    item.classList.toggle('is-highlighted', i === highlighted);
  });
}

function closeSuggestions() {
  suggestionsBox.classList.remove('is-open');
  suggestionsBox.innerHTML = '';
  highlighted = -1;
}

// Close dropdown when clicking outside
document.addEventListener('click', e => {
  if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
    closeSuggestions();
  }
});