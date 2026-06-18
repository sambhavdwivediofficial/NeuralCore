module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': '<rootDir>/jest.style-mock.js',
    '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/jest.file-mock.js',
    '^@/(.*)$': '<rootDir>/$1',
  },
  testPathIgnorePatterns: ['<rootDir>/node_modules/', '<rootDir>/.next/'],
  transform: {
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  transformIgnorePatterns: ['/node_modules/(?!(lucide-react)/)'],
};
