const API_KEY = 'ctgrfi1r01qhfodhmj8gctgrfi1r01qhfodhmj90'; 
const API_URL = `https://finnhub.io/api/v1/news?category=general&token=${API_KEY}`;

async function fetchNews() {
    try {
        const response = await fetch(API_URL);
        const news = await response.json();

        const newsContainer = document.getElementById('news-container');
        newsContainer.innerHTML = ''; 

        if (news.length > 0) {
            news.forEach(article => {
                const newsCard = document.createElement('div');
                newsCard.className = 'news-card';

                const title = document.createElement('h2');
                title.className = 'news-title';
                title.innerText = article.headline;

                const description = document.createElement('p');
                description.className = 'news-description';
                description.innerText = article.summary || 'No description available.';

                const link = document.createElement('a');
                link.className = 'news-link';
                link.href = article.url;
                link.target = '_blank';
                link.innerText = 'Read more';

                newsCard.appendChild(title);
                newsCard.appendChild(description);
                newsCard.appendChild(link);

                newsContainer.appendChild(newsCard);
            });
        } else {
            newsContainer.innerHTML = '<p class="has-text-centered has-text-grey">No news articles available.</p>';
        }
    } catch (error) {
        const newsContainer = document.getElementById('news-container');
        newsContainer.innerHTML = '<p class="has-text-centered has-text-danger">An error occurred while fetching news.</p>';
        console.error(error);
    }
}

document.addEventListener('DOMContentLoaded', fetchNews);
