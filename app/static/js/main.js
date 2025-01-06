document.addEventListener('DOMContentLoaded', function() {
    // Initialize all select elements with Tom Select
    const selects = {
        venue: initSelect('venue-select'),
        year: initSelect('year-select'),
        metrics: initSelect('metrics-select'),
        datasets: initSelect('datasets-select'),
        domains: initSelect('domains-select'),
        challenges: initSelect('challenges-select')
    };
    
    // Fetch and populate filter options
    fetch('/api/filters')
        .then(response => response.json())
        .then(data => {
            populateSelect(selects.venue, data.venues);
            populateSelect(selects.year, data.years);
            populateSelect(selects.metrics, data.metrics);
            populateSelect(selects.datasets, data.datasets);
            populateSelect(selects.domains, data.domains);
            populateSelect(selects.challenges, data.challenges);
        });

    // Handle filter application
    document.getElementById('apply-filters').addEventListener('click', function() {
        console.log('Applying filters...');
        applyFilters();
    });

    // Handle filter reset
    document.getElementById('reset-filters').addEventListener('click', function() {
        console.log('Resetting filters...');
        Object.values(selects).forEach(select => select.clear());
        document.getElementById('search-input').value = '';
        applyFilters();
    });

    // Initial load of papers
    applyFilters();

    // Add event listener for component filtering
    document.addEventListener('change', function(event) {
        if (event.target.classList.contains('component-list')) {
            filterByComponents(event);
        }
    });
});

function initSelect(id) {
    return new TomSelect('#' + id, {
        plugins: ['remove_button'],
        onItemAdd: function() {
            console.log('Item added to ' + id);
        },
        onItemRemove: function() {
            console.log('Item removed from ' + id);
        }
    });
}

function populateSelect(select, options) {
    const items = options.map(option => ({
        value: option,
        text: option
    }));
    select.addOptions(items);
}

function getSelectValues(selectId) {
    const select = document.getElementById(selectId).tomselect;
    return select ? Array.from(select.items) : [];
}

function applyFilters() {
    console.log('Getting current filter values...');
    const venues = getSelectValues('venue-select');
    const years = getSelectValues('year-select');
    const metrics = getSelectValues('metrics-select');
    const datasets = getSelectValues('datasets-select');
    const domains = getSelectValues('domains-select');
    const challenges = getSelectValues('challenges-select');
    const searchTerm = document.getElementById('search-input')?.value || '';

    console.log('Current filter values:', {
        venues, years, metrics, datasets, domains, challenges, searchTerm
    });

    const params = new URLSearchParams();
    if (venues.length) params.append('venues', venues.join(','));
    if (years.length) params.append('years', years.join(','));
    if (metrics.length) params.append('metrics', metrics.join(','));
    if (datasets.length) params.append('datasets', datasets.join(','));
    if (domains.length) params.append('domains', domains.join(','));
    if (challenges.length) params.append('challenges', challenges.join(','));
    if (searchTerm) params.append('search', searchTerm);

    const url = `/api/papers?${params.toString()}`;
    console.log('Sending request to:', url);

    htmx.ajax('GET', url, {
        target: '#papers-container',
        swap: 'innerHTML'
    }).then(() => {
        console.log('Papers updated successfully');
    }).catch(error => {
        console.error('Error updating papers:', error);
    });
}

function filterByComponents(event) {
    const checkboxes = document.querySelectorAll('.component-list input[type="checkbox"]:checked');
    const selectedComponents = Array.from(checkboxes).map(cb => cb.value);
    
    let url = '/api/papers';
    const params = new URLSearchParams(window.location.search);
    
    if (selectedComponents.length > 0) {
        params.set('components', selectedComponents.join(','));
    } else {
        params.delete('components');
    }
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    htmx.ajax('GET', url, '#papers-container');
}

// Add this function for toggling details
function toggleDetails(button) {
    const targetId = button.dataset.target;
    const detailsSection = document.getElementById(targetId);
    const icon = button.querySelector('.fas');
    
    if (detailsSection.classList.contains('is-hidden')) {
        detailsSection.classList.remove('is-hidden');
        button.setAttribute('aria-expanded', 'true');
        button.querySelector('span:not(.icon)').textContent = 'Hide Details';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    } else {
        detailsSection.classList.add('is-hidden');
        button.setAttribute('aria-expanded', 'false');
        button.querySelector('span:not(.icon)').textContent = 'Show Details';
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}
