# 웹 이미지 (배포용). 빌드한 dist 를 nginx 가 보내고, /api 는 Spring(server:8080)으로 넘긴다.
FROM node:22-alpine AS build
WORKDIR /src
# husky 는 git 이 없는 컨테이너에서 필요 없다
ENV HUSKY=0
RUN corepack enable

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
# 실제 API 를 쓴다. API 주소는 같은 도메인의 /api (nginx 가 넘김)
ENV VITE_USE_MOCK=false
ENV VITE_API_BASE_URL=
RUN pnpm build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
