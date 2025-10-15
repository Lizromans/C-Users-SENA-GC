document.addEventListener("DOMContentLoaded", () => {
	const carousels = document.querySelectorAll(".carousel-container");

	carousels.forEach((carousel) => {
		const track = carousel.querySelector(".carousel-track");
		const cards = track.querySelectorAll(".card");
		const dots = document.querySelectorAll(`.dots[data-carousel="${track.dataset.carousel}"] .dot`);
		const leftArrow = carousel.querySelector(".nav-arrow.left");
		const rightArrow = carousel.querySelector(".nav-arrow.right");

		let currentIndex = 0;
		let isAnimating = false;

		function updateCarousel(newIndex) {
			if (isAnimating) return;
			isAnimating = true;

			currentIndex = (newIndex + cards.length) % cards.length;

			cards.forEach((card, i) => {
				const offset = (i - currentIndex + cards.length) % cards.length;

				card.classList.remove("center", "left-1", "left-2", "right-1", "right-2", "hidden");

				if (offset === 0) {
					card.classList.add("center");
				} else if (offset === 1) {
					card.classList.add("right-1");
				} else if (offset === 2) {
					card.classList.add("right-2");
				} else if (offset === cards.length - 1) {
					card.classList.add("left-1");
				} else if (offset === cards.length - 2) {
					card.classList.add("left-2");
				} else {
					card.classList.add("hidden");
				}
			});

			dots.forEach((dot, i) => {
				dot.classList.toggle("active", i === currentIndex);
			});

			setTimeout(() => {
				isAnimating = false;
			}, 400);
		}

		leftArrow.addEventListener("click", () => updateCarousel(currentIndex - 1));
		rightArrow.addEventListener("click", () => updateCarousel(currentIndex + 1));

		dots.forEach((dot, i) => {
			dot.addEventListener("click", () => updateCarousel(i));
		});

		let touchStartX = 0;
		let touchEndX = 0;

		carousel.addEventListener("touchstart", (e) => {
			touchStartX = e.changedTouches[0].screenX;
		});

		carousel.addEventListener("touchend", (e) => {
			touchEndX = e.changedTouches[0].screenX;
			handleSwipe();
		});

		function handleSwipe() {
			const swipeThreshold = 50;
			const diff = touchStartX - touchEndX;

			if (Math.abs(diff) > swipeThreshold) {
				if (diff > 0) {
					updateCarousel(currentIndex + 1);
				} else {
					updateCarousel(currentIndex - 1);
				}
			}
		}

		updateCarousel(0);
	});
});
