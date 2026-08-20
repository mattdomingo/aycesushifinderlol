# Proposed Website Architecture

## Goal

Create a fast, mobile-friendly website for **Roll Call Sushi** that helps guests
understand the all-you-can-eat offering, browse the menu, and make a reservation
or start a takeout order.

## Recommended approach

Start with a static, server-rendered site. The current single-page menu is a
good foundation; keeping the site mostly static makes it inexpensive to host,
quick to load, and easy for restaurant staff to maintain. Add external booking
and ordering links rather than building payment or reservation systems in the
first release.

```
Guest browser
    |
    v
Static website (HTML, CSS, small JavaScript)
    |                 |                  |
    v                 v                  v
Menu content      Booking provider    Online ordering provider
```

## Site map

- **Home** — location, dining proposition, featured dishes, and primary calls
  to action for reservations and takeout.
- **Menu** — all-you-can-eat pricing, individual items, dietary markers, and
  dining policy.
- **About / Visit** — hours, address, parking or transit notes, photos, and a
  map link.
- **Contact** — phone number, email, and common guest questions.

For a very small launch, these sections can remain anchors on one page. As
content grows, move them to separate pages while keeping the same navigation.

## Front-end structure

```
index.html                 Home page and shared header/footer
menu.html                  Full menu and dietary information
visit.html                 Hours, location, and contact details
assets/
  css/site.css             Shared responsive styles and design tokens
  js/site.js               Small progressive enhancements only
  images/                  Optimized dish, restaurant, and social-preview images
data/
  menu.json                Optional structured menu source for future reuse
```

Use semantic HTML, keyboard-accessible navigation, descriptive image alt text,
and sufficient color contrast. The core information and telephone links should
work without JavaScript.

## Content and integrations

- Keep prices, hours, policies, and menu descriptions in one clearly labeled
  content source so updates are not missed across pages.
- Link the reservation button to a chosen booking service and the takeout button
  to the restaurant's ordering partner. Open third-party checkout flows only
  after explaining where the guest is going.
- Embed a map only if its performance cost is acceptable; otherwise use a
  lightweight map link.
- Add local-business structured data (JSON-LD) with the restaurant name,
  address, telephone number, hours, and menu URL.

## Deployment and operations

Host the static site on a CDN-backed static host. Configure a custom domain,
HTTPS, redirects for any retired URLs, and a simple analytics tool that respects
guest privacy. Before publishing menu or business information, have restaurant
staff verify it. A monthly content review should confirm hours, pricing,
allergen details, and outbound booking/ordering links.

## Future additions

Only introduce a backend when a clear need arises, such as staff-managed menu
updates, custom reservation rules, gift-card sales, or a newsletter. At that
point, use a small CMS or API-backed service behind the same static front end,
and keep customer payment data with the specialized payment provider rather
than the restaurant website.
