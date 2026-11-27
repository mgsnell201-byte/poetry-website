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


// Archive Grid Pagination & Search (12 items per page)
document.addEventListener('DOMContentLoaded', () => {
  const grid = document.querySelector('.media-grid[data-page-size]');
  const nav = document.getElementById('archive-pagination');
  if (!grid || !nav) return;

  const pageSize = parseInt(grid.dataset.pageSize || '12', 10);
  const allCards = Array.from(grid.querySelectorAll('.media-card'));
  const searchInput = document.getElementById('archive-search');
  const prevBtn = document.getElementById('page-prev');
  const nextBtn = document.getElementById('page-next');
  const statusEl = document.getElementById('page-status');
  let filteredCards = allCards;
  let currentPage = 1;

  const renderPage = (page) => {
    const totalPages = Math.max(1, Math.ceil(filteredCards.length / pageSize));
    currentPage = Math.max(1, Math.min(totalPages, page));
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    const visibleSet = new Set(filteredCards.slice(start, end));

    allCards.forEach((card) => {
      card.style.display = visibleSet.has(card) ? '' : 'none';
    });

    nav.hidden = filteredCards.length <= pageSize;
    statusEl.textContent = `Page ${currentPage} of ${totalPages}`;
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
  };

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      filteredCards = q
        ? allCards.filter((c) => (c.textContent || '').toLowerCase().includes(q))
        : allCards;
      renderPage(1);
    });
  }

  prevBtn.addEventListener('click', () => {
    renderPage(currentPage - 1);
    grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  nextBtn.addEventListener('click', () => {
    renderPage(currentPage + 1);
    grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  renderPage(1);
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
