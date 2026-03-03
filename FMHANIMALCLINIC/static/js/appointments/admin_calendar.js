/**
 * admin_calendar.js — Admin appointment calendar view
 * Renders Daily/Weekly/Monthly views with color-coding
 */

document.addEventListener("DOMContentLoaded", function () {
  const viewTabs = document.querySelectorAll("#viewTabs .appt-tab");
  const tableView = document.getElementById("tableView");
  const calendarView = document.getElementById("calendarView");
  const calContent = document.getElementById("calendarContent");
  const calLabel = document.getElementById("calLabel");
  const calPrev = document.getElementById("calPrev");
  const calNext = document.getElementById("calNext");
  const calToday = document.getElementById("calToday");
  const quickCreateModal = document.getElementById("quickCreateModal");
  const quickCreateBtn = document.getElementById("quickCreateBtn");
  const closeQuickCreate = document.getElementById("closeQuickCreate");
  const cancelQuickCreate = document.getElementById("cancelQuickCreate");

  const MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];
  const DAYS = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
  ];
  const DAYS_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  const STATUS_COLORS = {
    PENDING: "#f57c00",
    CONFIRMED: "#009688",
    CANCELLED: "#9e9e9e",
    COMPLETED: "#2e7d32",
  };

  const VET_COLORS = [
    "#009688",
    "#e63946",
    "#1e88e5",
    "#f57c00",
    "#8e24aa",
    "#2e7d32",
    "#d81b60",
    "#5c6bc0",
    "#00897b",
    "#f4511e",
  ];

  function getVetColor(vetId) {
    if (!vetId) return "#9e9e9e";
    return VET_COLORS[vetId % VET_COLORS.length];
  }

  let currentView = "table";
  let currentDate = new Date();
  let events = [];

  // ─── View Tab Switching ───
  viewTabs.forEach((tab) => {
    tab.addEventListener("click", function () {
      viewTabs.forEach((t) => t.classList.remove("active"));
      this.classList.add("active");
      currentView = this.dataset.view;

      const detailsContainer = document.getElementById("calendarDetailsContainer");
      if (detailsContainer) detailsContainer.style.display = "none";

      if (currentView === "table") {
        tableView.style.display = "";
        calendarView.style.display = "none";
      } else {
        tableView.style.display = "none";
        calendarView.style.display = "";
        loadCalendarView();
      }
    });
  });

  // ─── Calendar Navigation ───
  if (calPrev) calPrev.addEventListener("click", () => navigateCal(-1));
  if (calNext) calNext.addEventListener("click", () => navigateCal(1));
  if (calToday)
    calToday.addEventListener("click", () => {
      currentDate = new Date();
      loadCalendarView();
    });

  function navigateCal(delta) {
    if (currentView === "daily") {
      currentDate.setDate(currentDate.getDate() + delta);
    } else if (currentView === "weekly") {
      currentDate.setDate(currentDate.getDate() + delta * 7);
    } else if (currentView === "monthly") {
      currentDate.setMonth(currentDate.getMonth() + delta);
    }
    loadCalendarView();
  }

  // ─── Load Calendar ───
  async function loadCalendarView() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth() + 1;

    // Get filter values from the main form
    const branchFilter = document.querySelector('[name="branch"]');
    const vetFilter = document.querySelector('[name="vet"]');
    const statusFilter = document.querySelector('[name="status"]');

    let url = `${CALENDAR_API}?year=${year}&month=${month}`;
    if (branchFilter && branchFilter.value)
      url += `&branch=${branchFilter.value}`;
    if (vetFilter && vetFilter.value) url += `&vet=${vetFilter.value}`;
    if (statusFilter && statusFilter.value)
      url += `&status=${statusFilter.value}`;

    try {
      const res = await fetch(url);
      const data = await res.json();
      events = data.events || [];
    } catch (e) {
      events = [];
    }

    if (currentView === "daily") renderDailyView();
    else if (currentView === "weekly") renderWeeklyView();
    else if (currentView === "monthly") renderMonthlyView();
  }

  // ─── Daily View ───
  function renderDailyView() {
    const dateStr = currentDate.toISOString().split("T")[0];
    const dayName = DAYS[currentDate.getDay()];
    calLabel.textContent = `${dayName}, ${MONTHS[currentDate.getMonth()]} ${currentDate.getDate()}, ${currentDate.getFullYear()}`;

    const dayEvents = events
      .filter((e) => e.date === dateStr)
      .sort((a, b) => a.time.localeCompare(b.time));

    if (dayEvents.length === 0) {
      calContent.innerHTML = `
        <div class="empty-state" style="padding: 30px 0;">
          <i class='bx bx-calendar-x' style="font-size: 2.5rem;"></i>
          <h4>No appointments for this day</h4>
          <p>Use "Quick Create" to add an appointment.</p>
        </div>
      `;
      return;
    }

    let html = '<div class="schedule-entries">';
    dayEvents.forEach((e) => {
      const vetCol = getVetColor(e.vetId);
      const statusCol = STATUS_COLORS[e.status] || "#9e9e9e";
      html += `
        <a href="/appointments/admin/${e.id}/edit/" class="schedule-entry" style="border-left: 4px solid ${vetCol}; text-decoration: none; color: inherit;">
          <div class="schedule-entry-left">
            <div class="schedule-entry-avatar" style="background: ${vetCol};">${e.ownerName.charAt(0).toUpperCase()}</div>
            <div class="schedule-entry-info">
              <strong>${e.ownerName}</strong>
              <span>${e.petName}${e.petBreed ? " (" + e.petBreed + ")" : ""}</span>
            </div>
          </div>
          <div class="schedule-entry-details">
            <div class="schedule-entry-time">
              <i class='bx bx-time-five'></i> ${e.timeLabel}
            </div>
            <div class="schedule-entry-branch">
              <i class='bx bx-user'></i> ${e.vetName}
            </div>
            <span class="status-badge ${e.status.toLowerCase()}">${e.statusDisplay}</span>
          </div>
        </a>
      `;
    });
    html += "</div>";
    calContent.innerHTML = html;
  }

  // ─── Weekly View ───
  function renderWeeklyView() {
    const weekStart = new Date(currentDate);
    weekStart.setDate(weekStart.getDate() - weekStart.getDay());
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekEnd.getDate() + 6);

    calLabel.textContent = `${MONTHS[weekStart.getMonth()]} ${weekStart.getDate()} – ${MONTHS[weekEnd.getMonth()]} ${weekEnd.getDate()}, ${weekEnd.getFullYear()}`;

    let html = '<div class="weekly-grid">';
    for (let i = 0; i < 7; i++) {
      const day = new Date(weekStart);
      day.setDate(day.getDate() + i);
      const dateStr = day.toISOString().split("T")[0];
      const todayStr = new Date().toISOString().split("T")[0];
      const dayEvents = events
        .filter((e) => e.date === dateStr)
        .sort((a, b) => a.time.localeCompare(b.time));
      const isToday = dateStr === todayStr;

      html += `
        <div class="weekly-day ${isToday ? "today" : ""}" data-date="${dateStr}" style="cursor: pointer;">
          <div class="weekly-day-header">
            <span class="weekly-day-name">${DAYS_SHORT[i]}</span>
            <span class="weekly-day-num ${isToday ? "today-num" : ""}">${day.getDate()}</span>
          </div>
          <div class="weekly-day-events">
      `;
      dayEvents.forEach((e) => {
        const vetCol = getVetColor(e.vetId);
        // Changed to div with onclick for interactive modal
        html += `
          <div class="weekly-event" onclick="openAppointmentDetail(${e.id})" style="border-left: 3px solid ${vetCol}; cursor: pointer; display: flex; align-items: center; justify-content: space-between; padding: 6px 8px;">
            <div style="display: flex; flex-direction: column; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">
              <span class="weekly-event-time" style="font-size: 0.75rem; color: var(--text-2); margin-bottom: 2px;">${e.timeLabel}</span>
              <strong style="font-size: 0.85rem; color: var(--text-1);">${e.ownerName}</strong>
            </div>
            <span class="status-dot" style="background: ${STATUS_COLORS[e.status] || "#9e9e9e"}; width: 8px; height: 8px; flex-shrink: 0; margin-top: 2px; align-self: flex-start;"></span>
          </div>
        `;
      });
      if (dayEvents.length === 0) {
        html += `<div class="weekly-empty">No appts</div>`;
      }
      html += `
          </div>
        </div>
      `;
    }
    html += "</div>";
    calContent.innerHTML = html;

    // Attach listener for clicking any weekly day column
    const weeklyDays = calContent.querySelectorAll(".weekly-day");
    weeklyDays.forEach((dayEl) => {
      dayEl.addEventListener("click", function (e) {
        // Prevent overriding if an explicit 'weekly-event' inside is clicked
        if (e.target.closest(".weekly-event")) return;

        calContent.querySelectorAll(".weekly-day").forEach((d) => {
          d.classList.remove("selected-day");
          d.style.background = "";
        });

        this.classList.add("selected-day");
        this.style.background = "var(--bg-hover)";

        const clickedDate = this.getAttribute("data-date");
        if (clickedDate) {
          window.openMoreDetails(clickedDate);
        }
      });
    });
  }

  // ─── Monthly View ───
  function renderMonthlyView() {
    const detailsContainer = document.getElementById(
      "calendarDetailsContainer",
    );
    if (detailsContainer) detailsContainer.style.display = "none";

    calLabel.textContent = `${MONTHS[currentDate.getMonth()]} ${currentDate.getFullYear()}`;

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const todayStr = new Date().toISOString().split("T")[0];

    let html = '<div class="cal-weekdays">';
    DAYS_SHORT.forEach((d) => {
      html += `<div>${d}</div>`;
    });
    html += '</div><div class="cal-grid">';

    for (let i = 0; i < firstDay; i++) {
      html += '<div class="cal-day empty"></div>';
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const dayEvents = events.filter((e) => e.date === dateStr);
      const isToday = dateStr === todayStr;

      html += `
        <div class="cal-day ${isToday ? "today" : ""} ${dayEvents.length > 0 ? "has-events" : ""}" data-date="${dateStr}">
          <span class="cal-day-number">${d}</span>
          ${
            dayEvents.length > 0
              ? `
            <div class="cal-day-events">
              ${dayEvents
                .slice(0, 3)
                .map(
                  // Changed to div with onclick for interactive modal
                  (e) => `
                <div class="cal-event available" onclick="openAppointmentDetail(${e.id})" style="border-left: 3px solid ${getVetColor(e.vetId)}; cursor: pointer; padding: 2px 6px;">
                  <span class="cal-event-name" style="font-size: 0.75rem;">${e.timeLabel} <strong>${e.ownerName}</strong></span>
                </div>
              `,
                )
                .join("")}
              ${dayEvents.length > 3 ? `<div class="cal-event more" style="cursor: pointer; font-size: 0.75rem; text-align: center; color: var(--text-2); background: transparent;" onclick="openMoreDetails('${dateStr}')">+${dayEvents.length - 3} more</div>` : ""}
            </div>
          `
              : ""
          }
        </div>
      `;
    }

    html += "</div>";
    calContent.innerHTML = html;

    // Attach listener for clicking any day
    const calDays = calContent.querySelectorAll(".cal-day:not(.empty)");
    calDays.forEach((dayEl) => {
      dayEl.addEventListener("click", function(e) {
        // Prevent overriding if an explicit 'cal-event' block inside is clicked
        if (e.target.closest('.cal-event:not(.more)')) return;
        
        const clickedDate = this.getAttribute("data-date");
        if (clickedDate) {
          window.openMoreDetails(clickedDate);
        }
      });
    });
  }

  // ─── Render See More Details (Monthly 'more' click) ───
  window.openMoreDetails = function (dateStr) {
    const detailsContainer = document.getElementById(
      "calendarDetailsContainer",
    );
    if (!detailsContainer) return;

    calContent.querySelectorAll(".cal-day").forEach((d) => {
      d.classList.remove("selected-day");
      d.style.border = "";
      if (d.getAttribute("data-date") === dateStr) {
        d.classList.add("selected-day");
        d.style.border = "2px solid var(--primary)";
      }
    });

    const dayEvents = events
      .filter((e) => e.date === dateStr)
      .sort((a, b) => a.time.localeCompare(b.time));

    // Convert YYYY-MM-DD to friendly format
    const [year, month, dayObj] = dateStr.split("-");
    const dateObj = new Date(year, month - 1, dayObj);
    const formattedDate = `${DAYS[dateObj.getDay()]}, ${MONTHS[dateObj.getMonth()]} ${dateObj.getDate()}, ${dateObj.getFullYear()}`;

    let html = `
      <div style="padding: 16px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
        <h3 style="margin: 0; font-size: 1.1rem; color: var(--text-1);"><i class='bx bx-calendar-star' style="color: var(--primary);"></i> Appointments for ${formattedDate}</h3>
        <button class="btn-action outline" onclick="document.getElementById('calendarDetailsContainer').style.display='none'; document.querySelectorAll('.cal-day').forEach(d => { d.classList.remove('selected-day'); d.style.border=''; });" style="padding: 4px 10px; font-size: 0.8rem;"><i class='bx bx-x'></i> Close</button>
      </div>
      <div style="padding: 16px;">
        <div style="display: flex; flex-direction: column; gap: 12px;">
    `;

    dayEvents.forEach((e) => {
      const vetCol = getVetColor(e.vetId);
      html += `
        <div style="display: flex; align-items: center; border: 1px solid var(--border); border-left: 4px solid ${vetCol}; border-radius: 8px; padding: 12px 16px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.05); cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0,0,0,0.08)';" onmouseout="this.style.transform='none'; this.style.boxShadow='0 1px 3px rgba(0,0,0,0.05)';" onclick="openAppointmentDetail(${e.id})">
          
          <div style="display: flex; align-items: center; flex: 1;">
            <div style="width: 40px; height: 40px; border-radius: 8px; background: ${vetCol}; color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 1.2rem; margin-right: 16px;">
              ${e.ownerName.charAt(0).toUpperCase()}
            </div>
            <div>
              <div style="font-weight: 600; color: var(--text-1); font-size: 0.95rem;">${e.ownerName}</div>
              <div style="color: var(--text-2); font-size: 0.8rem;">${e.petName} ${e.petBreed ? '('+e.petBreed+')' : ''}</div>
            </div>
          </div>

          <div style="display: flex; align-items: center; gap: 16px; font-size: 0.85rem; color: var(--text-2);">
            <div style="display: flex; align-items: center; gap: 4px;"><i class='bx bx-time-five' style="color: var(--primary);"></i> ${e.timeLabel}</div>
            <div style="display: flex; align-items: center; gap: 4px;"><i class='bx bx-building' style="color: var(--primary);"></i> ${e.branchName || "Standard"}</div>
            <span class="source-badge source-walk-in" style="background: var(--bg-hover); color: var(--text-1);">${e.reason || 'Check-up'}</span>
            <span class="status-badge ${e.status.toLowerCase()}">${e.statusDisplay}</span>
          </div>

        </div>
      `;
    });

    html += `
        </div>
      </div>
    `;

    detailsContainer.innerHTML = html;
    detailsContainer.style.display = "block";
    detailsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // ─── Modal Detail Logic ───
  window.openAppointmentDetail = function (apptId) {
    const eventData = events.find((e) => e.id === apptId);
    if (!eventData) return;

    const modal = document.getElementById("appointmentDetailModal");
    if (!modal) return;

    // Set styling and border colors based on vet
    const vetCol = getVetColor(eventData.vetId);
    document.getElementById("detailModalHeader").style.borderLeftColor = vetCol;
    document.getElementById("detailVetAvatar").style.background = vetCol;

    // Setup Top Text
    document.getElementById("detailOwnerName").textContent =
      eventData.ownerName;
    document.getElementById("detailPetInfo").textContent =
      `${eventData.petName} (${eventData.petBreed || eventData.petSpecies})`;

    // Status Badge
    const statusB = document.getElementById("detailStatusBadge");
    statusB.className = `status-badge ${eventData.status.toLowerCase()}`;
    statusB.textContent = eventData.statusDisplay;

    // Timings
    document.getElementById("detailTime").textContent = eventData.timeLabel;
    const dObj = new Date(eventData.date);
    document.getElementById("detailDate").textContent =
      `${DAYS[dObj.getDay()]}, ${MONTHS[dObj.getMonth()]} ${dObj.getDate()}, ${dObj.getFullYear()}`;

    // Vet
    document.getElementById("detailVetAvatar").textContent = (
      eventData.vetName || "A"
    )
      .charAt(0)
      .toUpperCase();
    document.getElementById("detailVetName").textContent =
      eventData.vetName || "Any Available Vet";

    // Info Grids
    document.getElementById("detailBranch").textContent = eventData.branch;
    document.getElementById("detailReason").textContent = eventData.reason;
    document.getElementById("detailSourceBadge").className =
      `source-badge source-${eventData.source.toLowerCase()}`;
    document.getElementById("detailSourceBadge").textContent =
      eventData.source === "PORTAL" ? "Portal (Logged-in)" : "Walk-in (Public)";

    // Contact Info
    document.getElementById("detailPhone").textContent =
      eventData.ownerPhone || "-";
    document.getElementById("detailEmail").textContent =
      eventData.ownerEmail || "-";
    document.getElementById("detailCreatedAt").textContent =
      eventData.createdAt || "-";

    // Notes
    const notesContainer = document.getElementById("detailNotesContainer");
    if (eventData.notes) {
      document.getElementById("detailNotes").textContent = eventData.notes;
      notesContainer.style.display = "block";
    } else {
      notesContainer.style.display = "none";
      document.getElementById("detailNotes").textContent = "";
    }

    // Set Edit Link Path
    document.getElementById("detailEditBtn").href =
      `/appointments/admin/${eventData.id}/edit/`;

    // Open Modal
    modal.classList.add("active");
  };

  // Modal Close Logic
  const closeDetailBtn = document.getElementById("closeDetailModal");
  if (closeDetailBtn) {
    closeDetailBtn.addEventListener("click", () => {
      document
        .getElementById("appointmentDetailModal")
        .classList.remove("active");
    });
  }
  const apptModalOverlay = document.getElementById("appointmentDetailModal");
  if (apptModalOverlay) {
    apptModalOverlay.addEventListener("click", (e) => {
      if (e.target === apptModalOverlay) {
        apptModalOverlay.classList.remove("active");
      }
    });
  }

  // ─── Quick Create Modal ───
  function openModal(el) {
    el.classList.add("active");
  }
  function closeModal(el) {
    el.classList.remove("active");
  }

  if (quickCreateBtn)
    quickCreateBtn.addEventListener("click", () => openModal(quickCreateModal));
  if (closeQuickCreate)
    closeQuickCreate.addEventListener("click", () =>
      closeModal(quickCreateModal),
    );
  if (cancelQuickCreate)
    cancelQuickCreate.addEventListener("click", () =>
      closeModal(quickCreateModal),
    );
  if (quickCreateModal)
    quickCreateModal.addEventListener("click", (e) => {
      if (e.target === quickCreateModal) closeModal(quickCreateModal);
    });

  // ─── Quick Create Dynamic Dropdowns ───
  const qcBranch = document.querySelector('#quickCreateModal [name="branch"]');
  const qcVet = document.querySelector(
    '#quickCreateModal [name="preferred_vet"]',
  );
  const qcDate = document.querySelector(
    '#quickCreateModal [name="appointment_date"]',
  );
  const qcTime = document.querySelector("#id_quick_appointment_time");
  const qcTimeHint = document.getElementById("quickTimeHint");

  // Helper to show hints
  function showQCHint(msg, color = "#666") {
    if (qcTimeHint) {
      qcTimeHint.textContent = msg;
      qcTimeHint.style.color = color;
    }
  }

  // Fetch Vets when Branch changes
  function fetchQCVets() {
    if (!qcBranch || !qcVet) return;
    const branchId = qcBranch.value;
    const dateVal = qcDate ? qcDate.value : "";

    qcVet.innerHTML = '<option value="">Loading...</option>';

    if (!branchId) {
      qcVet.innerHTML = '<option value="">-- Select branch first --</option>';
      return;
    }

    let url = `/appointments/api/vets/?branch=${branchId}`;
    if (dateVal) url += `&date=${dateVal}`;

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        qcVet.innerHTML = '<option value="">-- Any Available Vet --</option>';
        data.vets.forEach((v) => {
          const opt = document.createElement("option");
          opt.value = v.id;
          opt.textContent = v.name;
          qcVet.appendChild(opt);
        });
      })
      .catch(() => {
        qcVet.innerHTML = '<option value="">-- Error loading vets --</option>';
      });
  }

  // Fetch Times when Vet, Branch, or Date changes
  function fetchQCTimes() {
    if (!qcBranch || !qcVet || !qcDate || !qcTime) return;

    const branchId = qcBranch.value;
    const vetId = qcVet.value;
    const dateVal = qcDate.value;

    qcTime.innerHTML = '<option value="">Loading times...</option>';

    if (!branchId || !dateVal) {
      qcTime.innerHTML =
        '<option value="">-- Select date and branch --</option>';
      showQCHint("Select a branch and date to load available times.");
      return;
    }

    let url = `/appointments/api/times/?branch=${branchId}&date=${dateVal}`;
    if (vetId) url += `&vet=${vetId}`;

    showQCHint("Checking availability...", "#1976d2");

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        qcTime.innerHTML = '<option value="">-- Select Time --</option>';
        if (data.times.length === 0) {
          showQCHint("⚠ No available slots for this date.", "#d32f2f");
          return;
        }

        let availableCount = 0;
        data.times.forEach((t) => {
          if (t.available) {
            availableCount++;
            const opt = document.createElement("option");
            opt.value = t.time;
            // E.g. "09:00 AM - 09:30 AM (Dr. Smith)"
            opt.textContent = `${t.label} ${vetId ? "" : `(${t.vet_name})`}`;
            qcTime.appendChild(opt);
          }
        });

        if (availableCount === 0) {
          showQCHint("⚠ All slots are booked for this selection.", "#d32f2f");
        } else {
          showQCHint(
            `✓ Found ${availableCount} available time slot(s).`,
            "#388e3c",
          );
        }
      })
      .catch(() => {
        qcTime.innerHTML = '<option value="">-- Error --</option>';
        showQCHint("Failed to load time slots.", "#d32f2f");
      });
  }

  // Bind Listeners
  if (qcBranch) {
    qcBranch.addEventListener("change", () => {
      fetchQCVets();
      fetchQCTimes();
    });
  }
  if (qcDate) {
    qcDate.addEventListener("change", () => {
      fetchQCVets();
      fetchQCTimes();
    });
  }
  if (qcVet) {
    qcVet.addEventListener("change", () => {
      fetchQCTimes();
    });
  }
});
