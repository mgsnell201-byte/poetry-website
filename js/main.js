document.addEventListener('DOMContentLoaded', () => {
  // Mobile navigation toggle
  const menuBtn = document.querySelector('.menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (menuBtn && navLinks) {
    menuBtn.setAttribute('aria-expanded', 'false');
    menuBtn.addEventListener('click', () => {
      const open = navLinks.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Inline track row play/pause
  const audio = new Audio();
  let activeBtn = null;
  let isPlaying = false;

  const stopPlayback = () => {
    audio.pause();
    isPlaying = false;
    document.querySelectorAll('.track-row').forEach((r) => r.classList.remove('is-playing'));
    document.querySelectorAll('.track-row .play-btn').forEach((b) => (b.textContent = '▶'));
  };

  document.querySelectorAll('.track-row .play-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const row = btn.closest('.track-row');
      const src = row?.dataset.src || '';
      if (!src) return;

      if (activeBtn === btn && isPlaying) {
        stopPlayback();
        return;
      }

      stopPlayback();
      activeBtn = btn;
      row?.classList.add('is-playing');
      audio.src = src;
      audio.play().then(() => {
        isPlaying = true;
        btn.textContent = '❚❚';
      }).catch(() => {
        stopPlayback();
      });
    });
  });

  audio.addEventListener('ended', stopPlayback);

  // Cloudflare Worker Comment Submission (/api/note)
  const form = document.getElementById('comment-form');
  const status = document.getElementById('comment-status');
  if (!form || !status) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalLabel = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';
    status.className = 'form-status';
    status.textContent = '';

    try {
      const formData = new FormData(form);
      const res = await fetch('/api/note', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok && data.success) {
        status.className = 'form-status is-success';
        status.textContent = 'Thank you — your comment has been sent.';
        form.reset();
      } else {
        status.className = 'form-status is-error';
        status.textContent = data.message || 'Could not send comment. Please try again.';
      }
    } catch (_) {
      status.className = 'form-status is-error';
      status.textContent = 'Could not send note. Please try again or email marvin@osmoticpoet.com.';
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = originalLabel;
    }
  });
});


// Archive Grid Pagination, Category Filters & Reading List
document.addEventListener('DOMContentLoaded', () => {
  const grid = document.querySelector('.media-grid[data-page-size]');
  const nav = document.getElementById('archive-pagination');
  if (grid && nav) {
    const pageSize = parseInt(grid.dataset.pageSize || '12', 10);
    const allCards = Array.from(grid.querySelectorAll('.media-card'));
    const filterBar = document.getElementById('poetry-filters') || document.getElementById('music-filters');
    const clearSavedBtn = document.getElementById('clear-saved');
    const prevBtn = document.getElementById('page-prev');
    const nextBtn = document.getElementById('page-next');
    const statusEl = document.getElementById('page-status');

    const sectionKey = window.location.pathname.startsWith('/music') ? 'music' : 'poetry';
    const savedKey = sectionKey === 'music' ? 'op_listening_list' : 'op_reading_list';
    const filteredListKey = sectionKey === 'music' ? 'op_filtered_tracks' : 'op_filtered_poems';
    const listLabel = sectionKey === 'music' ? 'Listening List' : 'Reading List';
    const itemNoun = sectionKey === 'music' ? 'tracks' : 'poems';
    const singularNoun = sectionKey === 'music' ? 'track' : 'poem';
    let savedSet = new Set();
    try {
      const rawSaved = JSON.parse(localStorage.getItem(savedKey) || '[]');
      if (Array.isArray(rawSaved)) savedSet = new Set(rawSaved);
    } catch (_) {}

    const params = new URLSearchParams(window.location.search);
    let activeFilter = params.get('saved') === '1'
      ? '__saved__'
      : (params.get('tag') || '__all__');
    const initialPage = parseInt(params.get('page') || '1', 10) || 1;
    let currentPage = initialPage;

    const getCardTags = (card) => (card.dataset.tags || '').split('|').filter(Boolean);

    const updateFilterCounts = () => {
      if (!filterBar) return;
      filterBar.querySelectorAll('.filter-pill[data-filter]').forEach((pill) => {
        const key = pill.dataset.filter;
        if (key === '__saved__') {
          const span = pill.querySelector('.saved-count');
          if (span) span.textContent = String(savedSet.size);
          return;
        }
        const span = pill.querySelector('.filter-count');
        if (!span) return;
        const count = key === '__all__'
          ? allCards.length
          : allCards.filter((c) => getCardTags(c).includes(key)).length;
        span.textContent = `(${count})`;
      });
      if (clearSavedBtn) {
        clearSavedBtn.hidden = savedSet.size === 0;
      }
    };

    const syncCardCheckboxes = () => {
      allCards.forEach((card) => {
        const box = card.querySelector('.card-select');
        const stem = card.dataset.stem || '';
        if (!box || !stem) return;
        const isSaved = savedSet.has(stem);
        box.classList.toggle('is-selected', isSaved);
        box.setAttribute('aria-checked', isSaved ? 'true' : 'false');
      });
    };

    const getFilteredCards = () => {
      if (activeFilter === '__all__' || !filterBar) return allCards;
      if (activeFilter === '__saved__') {
        return allCards.filter((c) => savedSet.has(c.dataset.stem || ''));
      }
      return allCards.filter((c) => getCardTags(c).includes(activeFilter));
    };

    const syncUrlAndSession = (filtered) => {
      const url = new URL(window.location.href);
      if (currentPage > 1) url.searchParams.set('page', String(currentPage));
      else url.searchParams.delete('page');
      url.searchParams.delete('q');
      if (activeFilter === '__saved__') {
        url.searchParams.set('saved', '1');
        url.searchParams.delete('tag');
      } else if (activeFilter !== '__all__') {
        url.searchParams.set('tag', activeFilter);
        url.searchParams.delete('saved');
      } else {
        url.searchParams.delete('tag');
        url.searchParams.delete('saved');
      }
      const nextUrl = url.pathname + url.search + url.hash;
      history.replaceState(null, '', nextUrl);
      try {
        sessionStorage.setItem(`op_last_archive:${sectionKey}`, nextUrl);
        if (activeFilter === '__all__') {
          sessionStorage.removeItem(filteredListKey);
        } else {
          const list = filtered.map((c) => ({
            stem: c.dataset.stem || '',
            title: c.querySelector('.media-card-title')?.textContent?.trim() || '',
          })).filter((item) => item.stem);
          sessionStorage.setItem(filteredListKey, JSON.stringify(list));
        }
      } catch (_) {}
    };

    let emptyMsg = null;

    const renderPage = (page) => {
      const filtered = getFilteredCards();
      const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
      currentPage = Math.max(1, Math.min(totalPages, page));
      const start = (currentPage - 1) * pageSize;
      const end = start + pageSize;
      const visibleSet = new Set(filtered.slice(start, end));

      allCards.forEach((card) => {
        card.style.display = visibleSet.has(card) ? '' : 'none';
      });

      if (filtered.length === 0) {
        if (!emptyMsg) {
          emptyMsg = document.createElement('p');
          emptyMsg.className = 'poem-stanza muted';
          grid.after(emptyMsg);
        }
        emptyMsg.textContent = activeFilter === '__saved__'
          ? `Your ${listLabel} is empty. Click the checkmark on any ${singularNoun} cover to add it.`
          : `No ${itemNoun} found in this category.`;
        emptyMsg.hidden = false;
      } else if (emptyMsg) {
        emptyMsg.hidden = true;
      }

      nav.hidden = filtered.length <= pageSize;
      statusEl.textContent = `Page ${currentPage} of ${totalPages}`;
      prevBtn.disabled = currentPage === 1;
      nextBtn.disabled = currentPage === totalPages;

      if (filterBar) {
        filterBar.querySelectorAll('.filter-pill[data-filter]').forEach((pill) => {
          pill.classList.toggle('is-active', pill.dataset.filter === activeFilter);
        });
      }

      syncUrlAndSession(filtered);
    };

    if (filterBar) {
      filterBar.addEventListener('click', (e) => {
        const pill = e.target.closest('.filter-pill[data-filter]');
        if (!pill) return;
        activeFilter = pill.dataset.filter || '__all__';
        renderPage(1);
      });
    }

    if (clearSavedBtn) {
      clearSavedBtn.addEventListener('click', () => {
        savedSet.clear();
        try { localStorage.removeItem(savedKey); } catch (_) {}
        syncCardCheckboxes();
        updateFilterCounts();
        if (activeFilter === '__saved__') {
          activeFilter = '__all__';
        }
        renderPage(1);
      });
    }

    grid.addEventListener('click', (e) => {
      const box = e.target.closest('.card-select');
      if (!box) return;
      e.preventDefault();
      e.stopPropagation();
      const card = box.closest('.media-card');
      const stem = card?.dataset.stem || '';
      if (!stem) return;
      if (savedSet.has(stem)) savedSet.delete(stem);
      else savedSet.add(stem);
      try { localStorage.setItem(savedKey, JSON.stringify(Array.from(savedSet))); } catch (_) {}
      syncCardCheckboxes();
      updateFilterCounts();
      if (activeFilter === '__saved__') {
        renderPage(currentPage);
      }
    });

    grid.addEventListener('keydown', (e) => {
      if (e.key !== ' ' && e.key !== 'Enter') return;
      const box = e.target.closest('.card-select');
      if (!box) return;
      e.preventDefault();
      e.stopPropagation();
      box.click();
    });

    prevBtn.addEventListener('click', () => {
      renderPage(currentPage - 1);
      grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    nextBtn.addEventListener('click', () => {
      renderPage(currentPage + 1);
      grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    syncCardCheckboxes();
    updateFilterCounts();
    renderPage(initialPage);
  }

  // Smart "Previous page" breadcrumb & filtered Previous/Next Poem nav
  const breadcrumb = document.querySelector('a.breadcrumb');
  if (breadcrumb) {
    const sectionKey = window.location.pathname.startsWith('/music') ? 'music' : 'poetry';
    let backUrl = '';
    try {
      if (document.referrer) {
        const ref = new URL(document.referrer);
        if (
          ref.origin === window.location.origin &&
          (ref.pathname === `/${sectionKey}` ||
            ref.pathname === `/${sectionKey}/` ||
            ref.pathname === `/${sectionKey}/index.html`)
        ) {
          backUrl = ref.pathname + ref.search + ref.hash;
        }
      }
      if (!backUrl) {
        const saved = sessionStorage.getItem(`op_last_archive:${sectionKey}`);
        if (saved) backUrl = saved;
      }
    } catch (_) {}
    if (backUrl) {
      breadcrumb.setAttribute('href', backUrl);
    }

    const filteredListKey = sectionKey === 'music' ? 'op_filtered_tracks' : 'op_filtered_poems';
    const pieceLabel = sectionKey === 'music' ? 'Track' : 'Poem';
    try {
      const rawList = sessionStorage.getItem(filteredListKey);
      const pieceNav = document.querySelector('.piece-nav');
      if (rawList && pieceNav) {
        const list = JSON.parse(rawList);
        const currentSlug = window.location.pathname
          .replace(new RegExp(`^/${sectionKey}/`), '')
          .replace(/\.html$/, '');
        const idx = Array.isArray(list) ? list.findIndex((p) => p.stem === currentSlug) : -1;
        if (idx !== -1) {
          const prev = idx > 0 ? list[idx - 1] : null;
          const next = idx + 1 < list.length ? list[idx + 1] : null;
          pieceNav.innerHTML = '';
          const makeBtn = (item, label, isNext) => {
            const el = document.createElement(item ? 'a' : 'span');
            el.className = item ? 'piece-nav-btn' : 'piece-nav-btn is-disabled';
            el.textContent = isNext ? `${label} \u2192` : `\u2190 ${label}`;
            if (item) {
              el.href = `${item.stem}.html`;
              if (item.title) el.title = item.title;
            } else {
              el.setAttribute('aria-disabled', 'true');
            }
            return el;
          };
          pieceNav.appendChild(makeBtn(prev, `Previous ${pieceLabel}`, false));
          pieceNav.appendChild(makeBtn(next, `Next ${pieceLabel}`, true));
        }
      }
    } catch (_) {}
  }
});

// Thumbs Up / Down Counter
document.addEventListener('DOMContentLoaded', () => {
  const bar = document.querySelector('.vote-bar[data-vote-id]');
  if (!bar) return;

  const id = bar.dataset.voteId;
  const upBtn = bar.querySelector('[data-vote="up"]');
  const downBtn = bar.querySelector('[data-vote="down"]');
  const upCount = upBtn?.querySelector('.vote-count');
  const downCount = downBtn?.querySelector('.vote-count');
  if (!id || !upBtn || !downBtn || !upCount || !downCount) return;

  const storageKey = `op_vote:${id}`;
  let currentVote = '';
  try {
    currentVote = localStorage.getItem(storageKey) || '';
  } catch (_) {}

  const renderState = (up, down) => {
    upCount.textContent = String(up);
    downCount.textContent = String(down);
    upBtn.classList.toggle('is-active', currentVote === 'up');
    downBtn.classList.toggle('is-active', currentVote === 'down');
    upBtn.setAttribute('aria-pressed', currentVote === 'up' ? 'true' : 'false');
    downBtn.setAttribute('aria-pressed', currentVote === 'down' ? 'true' : 'false');
  };

  renderState(0, 0);

  fetch(`/api/votes?id=${encodeURIComponent(id)}`)
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => {
      if (data && typeof data.up === 'number' && typeof data.down === 'number') {
        renderState(data.up, data.down);
      }
    })
    .catch(() => {});

  let busy = false;
  const castVote = async (choice) => {
    if (busy) return;
    busy = true;
    const prev = currentVote;
    const next = prev === choice ? '' : choice;
    const curUp = parseInt(upCount.textContent || '0', 10) || 0;
    const curDown = parseInt(downCount.textContent || '0', 10) || 0;
    const optUp = Math.max(0, curUp + (next === 'up' ? 1 : 0) - (prev === 'up' ? 1 : 0));
    const optDown = Math.max(0, curDown + (next === 'down' ? 1 : 0) - (prev === 'down' ? 1 : 0));

    currentVote = next;
    renderState(optUp, optDown);

    try {
      const res = await fetch('/api/votes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, prev, next }),
      });
      if (res.ok) {
        const data = await res.json();
        try {
          if (next) localStorage.setItem(storageKey, next);
          else localStorage.removeItem(storageKey);
        } catch (_) {}
        if (typeof data.up === 'number' && typeof data.down === 'number') {
          renderState(data.up, data.down);
        }
      } else {
        currentVote = prev;
        renderState(curUp, curDown);
      }
    } catch (_) {
      currentVote = prev;
      renderState(curUp, curDown);
    } finally {
      busy = false;
    }
  };

  upBtn.addEventListener('click', () => castVote('up'));
  downBtn.addEventListener('click', () => castVote('down'));
});

// Casual Copy & Right-Click Deterrents
document.addEventListener('contextmenu', (e) => {
  if (e.target.closest('.piece-cover, .media-card-img, .bio-photo, .piece-video, .poem-stanza, .piece-title')) {
    e.preventDefault();
  }
});

document.addEventListener('dragstart', (e) => {
  if (e.target instanceof HTMLImageElement) {
    e.preventDefault();
  }
});

['copy', 'cut'].forEach((evt) => {
  document.addEventListener(evt, (e) => {
    if (!e.target.closest('input, textarea')) {
      e.preventDefault();
    }
  });
});
