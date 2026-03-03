/**
 * booking.js — Smart booking with availability engine
 * Handles Scenario A (no vet → any slots) and Scenario B (vet → restricted dates/times)
 */
document.addEventListener("DOMContentLoaded", function () {
  const branchSelect = document.querySelector('[name="branch"]');
  const dateInput = document.querySelector('[name="appointment_date"]');
  const vetSelect = document.querySelector('[name="preferred_vet"]');
  const timeInput = document.querySelector('[name="appointment_time"]');
  const timeHint = document.getElementById("timeHint");
  const timeSlotsGrid = document.getElementById("timeSlotsGrid");

  if (!branchSelect || !vetSelect) return;

  // Set min date to today
  if (dateInput) {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    dateInput.setAttribute("min", yyyy + "-" + mm + "-" + dd);
  }

  // Store available dates for vet-specific filtering
  let vetAvailableDates = null;

  /**
   * Fetch available vets when branch or date changes
   */
  function fetchVets() {
    const branch = branchSelect.value;
    const dt = dateInput ? dateInput.value : "";

    vetSelect.innerHTML = '<option value="">Loading...</option>';

    if (!branch) {
      vetSelect.innerHTML = '<option value="">— Select branch first —</option>';
      return;
    }

    let url = API_VETS + "?branch=" + branch;
    if (dt) url += "&date=" + dt;

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        vetSelect.innerHTML =
          '<option value="">— No preferred vet (any available) —</option>';
        data.vets.forEach((v) => {
          const opt = document.createElement("option");
          opt.value = v.id;
          opt.textContent = v.name;
          vetSelect.appendChild(opt);
        });
      })
      .catch(() => {
        vetSelect.innerHTML =
          '<option value="">— Could not load vets —</option>';
      });
  }

  /**
   * Fetch and display available time slots
   */
  function fetchTimeSlots() {
    const vet = vetSelect.value;
    const dt = dateInput ? dateInput.value : "";
    const branch = branchSelect.value;

    if (!dt || !branch) {
      showTimeHint("Select a branch and date to see available time slots.");
      clearTimeSlots();
      return;
    }

    // If vet-specific dates are loaded and this date is not available, show a message
    if (vet && vetAvailableDates && !vetAvailableDates.includes(dt)) {
      showTimeHint(
        "⚠ This vet is not scheduled on this date. Please pick a highlighted date.",
        "#e65100",
      );
      clearTimeSlots();
      return;
    }

    let url = API_TIMES + "?date=" + dt + "&branch=" + branch;
    if (vet) url += "&vet=" + vet;

    showTimeHint("Loading available slots...");

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        if (data.times.length === 0) {
          if (vet) {
            showTimeHint(
              "No available slots for this vet on this date. Try another date.",
              "#e65100",
            );
          } else {
            showTimeHint(
              "No scheduled vets on this date. You can still pick a time manually.",
            );
          }
          clearTimeSlots();
          if (timeInput) timeInput.removeAttribute("readonly");
          return;
        }

        renderTimeSlots(data.times);

        if (vet) {
          showTimeHint("✓ Select an available time slot below:", "#009688");
        } else {
          showTimeHint("✓ Available slots from all scheduled vets:", "#009688");
        }
      })
      .catch(() => {
        showTimeHint("Could not load time slots.", "#e65100");
        clearTimeSlots();
      });
  }

  /**
   * Render clickable time slot grid with range display
   * Booked slots appear greyed out with "Appointed already" label
   */
  function renderTimeSlots(slots) {
    if (!timeSlotsGrid) return;
    timeSlotsGrid.innerHTML = "";
    timeSlotsGrid.style.display = "grid";

    slots.forEach((slot) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "time-slot-btn" + (slot.available ? "" : " disabled booked");
      btn.innerHTML = `
        <span class="time-slot-time">${slot.label}</span>
        ${slot.available ? "" : `<span class="time-slot-booked">${slot.booked_label || "Appointed already"}</span>`}
        ${slot.available && slot.vet_name ? `<span class="time-slot-vet">${slot.vet_name}</span>` : ""}
        ${slot.available && slot.shift_type ? `<span class="time-slot-shift">${slot.shift_type}</span>` : ""}
      `;
      btn.dataset.time = slot.time;
      btn.dataset.vetId = slot.vet_id || "";
      btn.dataset.vetName = slot.vet_name || "";

      if (slot.available) {
        btn.addEventListener("click", function () {
          // Deselect all
          timeSlotsGrid
            .querySelectorAll(".time-slot-btn")
            .forEach((b) => b.classList.remove("selected"));
          // Select this
          this.classList.add("selected");
          // Set the time value
          if (timeInput) timeInput.value = slot.time;
          // Set the preferred vet from the slot
          if (vetSelect && slot.vet_id) {
            // Ensure the vet option exists in the dropdown
            let optionExists = false;
            for (let i = 0; i < vetSelect.options.length; i++) {
              if (vetSelect.options[i].value == slot.vet_id) {
                optionExists = true;
                break;
              }
            }
            if (!optionExists) {
              const opt = document.createElement("option");
              opt.value = slot.vet_id;
              opt.textContent = slot.vet_name;
              vetSelect.appendChild(opt);
            }
            vetSelect.value = slot.vet_id;
          }
        });
      }

      timeSlotsGrid.appendChild(btn);
    });
  }

  function clearTimeSlots() {
    if (timeSlotsGrid) {
      timeSlotsGrid.innerHTML = "";
      timeSlotsGrid.style.display = "none";
    }
  }

  function showTimeHint(text, color) {
    if (timeHint) {
      timeHint.innerHTML = "<i class='bx bx-info-circle'></i> " + text;
      timeHint.style.color = color || "var(--text-3)";
    }
  }

  /**
   * Scenario B: If vet is selected, fetch available dates and disable unavailable ones
   */
  function updateDateAvailability() {
    const vet = vetSelect.value;
    const branch = branchSelect.value;

    if (!vet || !dateInput || !branch) {
      vetAvailableDates = null;
      return;
    }

    // Calculate month/year based on current date input or now
    const currentVal = dateInput.value;
    const refDate = currentVal
      ? new Date(currentVal + "T00:00:00")
      : new Date();
    const year = refDate.getFullYear();
    const month = refDate.getMonth() + 1;

    const url = `${API_DATES}?vet=${vet}&year=${year}&month=${month}&branch=${branch}`;

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        vetAvailableDates = data.dates || [];
        if (vetAvailableDates.length === 0) {
          showTimeHint(
            "⚠ This vet has no scheduled dates this month. Try a different vet or month.",
            "#e65100",
          );
        } else {
          showTimeHint(
            `✓ This vet is available on ${vetAvailableDates.length} date(s) this month.`,
            "#009688",
          );
        }

        // If current date is selected but not available, clear it
        if (currentVal && !vetAvailableDates.includes(currentVal)) {
          dateInput.value = "";
          clearTimeSlots();
          showTimeHint(
            `⚠ Your selected date is not in this vet's schedule. Please pick an available date.`,
            "#e65100",
          );
        }
      })
      .catch(() => {
        vetAvailableDates = null;
      });
  }

  // ─── Event Listeners ───

  branchSelect.addEventListener("change", function () {
    fetchVets();
    clearTimeSlots();
    vetAvailableDates = null;
    showTimeHint(
      "Select a date and optionally a vet to see available time slots.",
    );
  });

  if (dateInput) {
    dateInput.addEventListener("change", function () {
      fetchVets();
      fetchTimeSlots();
    });
  }

  vetSelect.addEventListener("change", function () {
    if (this.value) {
      updateDateAvailability();
    } else {
      vetAvailableDates = null;
      showTimeHint("Select a date to see all available time slots.");
    }
    if (dateInput && dateInput.value) {
      fetchTimeSlots();
    }
  });
});
