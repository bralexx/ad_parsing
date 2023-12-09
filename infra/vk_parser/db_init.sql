create database if not exists vk_scrap;

create table if not exists vk_scrap.walls (
  owner_id int,
  domain varchar(255),
  is_parsed bool default false,
  CONSTRAINT unique_owner UNIQUE (owner_id),
  constraint unique_domain unique (domain)
);

create table if not exists vk_scrap.posts (
  owner_id int,
  id int,
  primary key (owner_id, id),
  date datetime,
  text text,
  other json
);

create user if not exists 'scraper'@'localhost';

grant select, insert on vk_scrap.posts to 'scraper'@'localhost';
grant select, insert, update on vk_scrap.walls to 'scraper'@'localhost';