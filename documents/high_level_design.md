# Tool Room Inventory

This repo contains software for managing the inventory and sign-out process 
for the tools in a machine shop.

## Terminology

1. TRI - Tool Room Inventory
2. BCR - Burlington Community Robotics

## Entities

1. Tool
	- Has a name, picture, ID, description (optional).
2. User. Each team member has an ID card (BCR card). 
3. Admin. Administrates the TRI. 

## Use cases

1. As a team member, I can use TRI to borrow tools from the inventory.
2. As an Admin, I can use TRI to add/remove/edit tools in the inventory.
3. As any user (User or Admin), I can see a dashboard of tools signed out of 
	the inventory.
4. As any user, I can see a dashboard of tools available to sign out of the 
	inventory.