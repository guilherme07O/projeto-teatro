-- Banco separado para os testes automatizados.
--
-- Roda apenas na primeira inicialização do volume (docker-entrypoint-initdb.d).
-- Isola o banco de teste (teatro_test) do banco de desenvolvimento (teatro):
-- o conftest.py dos testes executa DROP/CREATE TABLE e semeia apenas 10 assentos,
-- então apontar os testes para "teatro" apagaria os 300 assentos de desenvolvimento.
CREATE DATABASE IF NOT EXISTS teatro_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON teatro_test.* TO 'app'@'%';
FLUSH PRIVILEGES;
