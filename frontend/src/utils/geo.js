// Capture the device GPS position. Resolves to {} if unavailable/denied so the
// caller can still proceed (visit logging never blocks on location).
export function getPosition(opts = {}) {
	return new Promise((resolve) => {
		if (!navigator.geolocation) return resolve({})
		navigator.geolocation.getCurrentPosition(
			(pos) =>
				resolve({
					latitude: pos.coords.latitude,
					longitude: pos.coords.longitude,
					accuracy: pos.coords.accuracy,
				}),
			() => resolve({}),
			{ enableHighAccuracy: true, timeout: 10000, maximumAge: 0, ...opts }
		)
	})
}

export function mapsLink(lat, lng) {
	if (lat == null || lng == null) return null
	return `https://www.google.com/maps?q=${lat},${lng}`
}
