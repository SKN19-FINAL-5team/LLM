FROM node:22-alpine

WORKDIR /app

# package.json package-lock.json 
COPY package*.json ./

#  
RUN npm install

#   
COPY . .

#  
EXPOSE 5173

#   
CMD ["npm", "run", "dev", "--", "--host"]
