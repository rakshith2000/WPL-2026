const statLabels = [
            { key: "Mats", label: "MAT" },
            { key: "Inns", label: "INNS" },
            { key: "N/O", label: "N/O" },
            { key: "Runs", label: "RUNS" },
            { key: "HS", label: "HS" },
            { key: "Avg", label: "AVG" },
            { key: "SR", label: "SR" },
            { key: "100s", label: "100S" },
            { key: "50s", label: "50S" },
            { key: "4s", label: "4S" },
            { key: "6s", label: "6S" },
            { key: "Ducks", label: "DUCKS" },
            { key: "CT", label: "CT" },
            { key: "ST", label: "ST" },
            { key: "Team", label: "TEAM" }
        ];
        const bowlingStatLabels = [
            { key: "Mats", label: "MAT" },
            { key: "Inns", label: "INNS" },
            { key: "Overs", label: "OVERS" },
            { key: "Mdns", label: "MDNS" },
            { key: "Runs", label: "RUNS" },
            { key: "Wkts", label: "WKTS" },
            { key: "BBI", label: "BBI" },
            { key: "Avg", label: "AVG" },
            { key: "Econ", label: "ECON" },
            { key: "SR", label: "SR" },
            { key: "3W", label: "3W" },
            { key: "5W", label: "5W" },
            { key: "Team", label: "TEAM"}
        ];

        console.log(statsData);

        // Utility: get all years (including overall if present) for dropdown
        function getAvailableYears(stats) {
            const keys = Object.keys(stats);
            let years = keys.filter(y => y !== 'overall' && stats[y] && (stats[y]["Batting & Fielding"] || stats[y]["Bowling"]));
            years = years.sort((a, b) => b.localeCompare(a)); // descending order
            if (stats['overall'] && (stats['overall']["Batting & Fielding"] || stats['overall']["Bowling"])) {
                years.unshift('overall');
            }
            return years;
        }
        // Utility: get all years for horizontal table (original order in data)
        function getYearsForHorizontal(stats) {
            return Object.keys(stats).filter(y => stats[y] && (stats[y]["Batting & Fielding"] || stats[y]["Bowling"]));
        }

        // Utility: get headers for a category (batting/bowling) from the first available year
        function getHeaders(stats, category) {
            for (const y of Object.keys(stats)) {
                if (stats[y] && stats[y][category]) {
                    return Object.keys(stats[y][category]);
                }
            }
            return [];
        }

        // Render dropdown dynamically
        function renderDropdown(years, selectedYear) {
            if (!years.length) {
                document.querySelector('.stats-dropdown-container').style.display = 'none';
                return;
            }
            document.querySelector('.stats-dropdown-container').style.display = 'block';
            let menu = years.map(y => `<a href="#" data-value="${y}" class="${y===selectedYear?'activeD':''}" onclick="selectYear(event, '${y}')">${y}</a>`).join('');
            document.getElementById('dropdownMenu').innerHTML = menu;
            document.getElementById('dropdownLabel').textContent = selectedYear;
        }

        // Render vertical table for a category and year (filtered by statLabels)
        function renderVerticalTable(stats, year, category, containerId) {
            const data = stats[year] && stats[year][category];
            if (!data) {
                document.getElementById(containerId).innerHTML = '';
                return;
            }
            const labels = category === 'Batting & Fielding' ? statLabels : bowlingStatLabels;
            let html = `<table><thead><tr><th>${category.toUpperCase()}</th><th>${year.toUpperCase()}</th></tr></thead><tbody>`;
            labels.forEach(({key, label}) => {
                html += `<tr><td>${label}</td><td>${data[key] ?? '-'}</td></tr>`;
            });
            html += '</tbody></table>';
            document.getElementById(containerId).innerHTML = html;
        }

        // Render horizontal table for a category (filtered by statLabels)
        function renderHorizontalTable(stats, years, category, containerId) {
            const labels = category === 'Batting & Fielding' ? statLabels : bowlingStatLabels;
            if (!labels.length) {
                document.getElementById(containerId).innerHTML = '';
                return;
            }
            let html = `<table><thead><tr><th>${category.toUpperCase()}</th>`;
            labels.forEach(({label}) => html += `<th>${label}</th>`);
            html += '</tr></thead><tbody>';
            years.forEach(y => {
                const row = stats[y] && stats[y][category];
                if (row) {
                    html += `<tr><td>${y}</td>`;
                    labels.forEach(({key}) => html += `<td>${row[key] ?? '-'}</td>`);
                    html += '</tr>';
                }
            });
            html += '</tbody></table>';
            document.getElementById(containerId).innerHTML = html;
        }

        // Main render function
        function renderStats(selectedYear) {
            const dropdownYears = getAvailableYears(statsData);
            const tableYears = getYearsForHorizontal(statsData);
            if (!dropdownYears.length || !statsData[selectedYear]) {
                document.querySelector('.stats-dropdown-container').style.display = 'none';
                document.getElementById('verticalTable').innerHTML = '';
                document.getElementById('verticalBowlingTable').innerHTML = '';
                document.getElementById('horizontalTable').innerHTML = '';
                document.getElementById('horizontalBowlingTable').innerHTML = '';
                document.querySelector('.stats-container').innerHTML += '<div class="no-data">DATA NOT AVAILABLE</div>';
                return;
            }
            // Remove any previous no-data message
            const noData = document.querySelector('.no-data');
            if (noData) noData.remove();
            renderDropdown(dropdownYears, selectedYear);
            renderVerticalTable(statsData, selectedYear, 'Batting & Fielding', 'verticalTable');
            renderVerticalTable(statsData, selectedYear, 'Bowling', 'verticalBowlingTable');
            renderHorizontalTable(statsData, tableYears, 'Batting & Fielding', 'horizontalTable');
            renderHorizontalTable(statsData, tableYears, 'Bowling', 'horizontalBowlingTable');
        }

        // Dropdown logic
        function toggleDropdown() {
            const dropdown = document.getElementById('yearDropdown');
            dropdown.classList.toggle('show');
            document.getElementById('dropdownChevron').classList.toggle('rotate');
        }
        function selectYear(event, year) {
            event.preventDefault();
            renderStats(year);
            // Remove active class from all
            document.querySelectorAll('#dropdownMenu a').forEach(a => a.classList.remove('activeD'));
            // Add active class to selected
            event.target.classList.add('activeD');
            document.getElementById('yearDropdown').classList.remove('show');
            document.getElementById('dropdownChevron').classList.remove('rotate');
        }
        // Initial render
        const defaultYear = getAvailableYears(statsData)[0] || '';
        renderStats(defaultYear);
        // Close dropdown if clicked outside
        document.addEventListener('click', function(e) {
            const dropdown = document.getElementById('yearDropdown');
            if (!dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
                document.getElementById('dropdownChevron').classList.remove('rotate');
            }
        });