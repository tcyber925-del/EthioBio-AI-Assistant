# ADR-0001: Dashboard redesign cutover strategy — build alongside, swap atomically

The dashboard UI is undergoing a full visual redesign (light mode, teal accent, minimal card system, collapsible sidebar). We chose to build new components in `src/components/dashboard-v2/` and keep existing components untouched, rather than migrating in-place.

This avoids regressions on 19+ existing pages during development. Each page is cut over atomically by routing the v2 component under the existing route. When a page is verified, the old component is deleted. During migration, the old Sidebar hides itself on v2 routes via a `pathname` check.

Only low-write-contention files (tailwind.config, globals.css) are shared between old and new — all component code lives in separate files until cutover.
