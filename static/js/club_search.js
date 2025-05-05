document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('club-search');
    const searchButton = document.getElementById('search-button');
    const searchFeedback = document.getElementById('search-feedback');
    const clubsContainer = document.getElementById('clubs-container');
    let debounceTimer;

    function debounce(func, delay) {
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => func.apply(context, args), delay);
        };
    }

    function renderClubs(clubs) {
        if (clubs.length === 0) {
            clubsContainer.innerHTML = `
                <div class="col-12">
                    <p class="text-center">No clubs found matching your search.</p>
                </div>
            `;
            return;
        }

        const clubsHtml = clubs.map(club => `
            <div class="col-md-4 mb-4">
                <div class="card h-100">
                    ${club.logo ? `<img src="${club.logo}" class="card-img-top" alt="${club.name}">` : ''}
                    <div class="card-body">
                        <h5 class="card-title">${club.name}</h5>
                        <p class="card-text">${club.description ? club.description.split(' ').slice(0, 30).join(' ') + '...' : ''}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <a href="/clubs/${club.id}/" class="btn btn-primary">View Details</a>
                            <small class="text-muted">Created ${new Date(club.created_at).toLocaleDateString()}</small>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        clubsContainer.innerHTML = clubsHtml;
    }

    async function performSearch() {
        const query = searchInput.value.trim();

        // Show loading state
        searchButton.disabled = true;
        searchFeedback.textContent = 'Searching...';
        searchFeedback.style.display = 'block';

        try {
            const response = await fetch(`/clubs/search/?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Search failed');
            
            const data = await response.json();
            renderClubs(data.clubs);
            
            // Update feedback only for errors
            searchFeedback.style.display = 'none';
        } catch (error) {
            searchFeedback.textContent = 'Error performing search. Please try again.';
            searchFeedback.style.display = 'block';
            console.error('Search error:', error);
        } finally {
            searchButton.disabled = false;
        }
    }

    // Handle search button click
    searchButton.addEventListener('click', performSearch);

    // Handle enter key press
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch();
        }
    });

    // Handle input changes with debouncing
    searchInput.addEventListener('input', debounce(performSearch, 300));
});