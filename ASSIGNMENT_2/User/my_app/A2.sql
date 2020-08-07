CREATE DATABASE IF NOT EXISTS A2;
USE A2;
CREATE TABLE IF NOT EXISTS `user` (
	`id` int(11) NOT NULL AUTO_INCREMENT,
  	`username` varchar(50) NOT NULL,
  	`password` varchar(255) NOT NULL,
    `salt` varchar(255) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
create table images(
		id int,
        imagename varchar(50) NOT NULL,
        original varchar(2048) NOT NULL,
        obj varchar(2048) NOT NULL,
        thumbnails varchar(2048) NOT NULL,
        foreign key (id) references user(id)
);