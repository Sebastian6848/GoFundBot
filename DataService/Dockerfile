FROM node:20-slim AS prod
EXPOSE 3100

WORKDIR /app
COPY ./dist /app
RUN npm install

CMD ["node", "index.js"]
