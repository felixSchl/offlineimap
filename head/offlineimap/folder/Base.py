# Base folder support
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

class BaseFolder:
    def getname(self):
        """Returns name"""
        return self.name

    def getroot(self):
        """Returns the root of the folder, in a folder-specific fashion."""
        return self.root

    def getsep(self):
        """Returns the separator for this folder type."""
        return self.sep

    def getfullname(self):
        if self.getroot():
            return self.getroot() + self.getsep() + self.getname()
        else:
            return self.getname()
    
    def isuidvalidityok(self, remotefolder):
        raise NotImplementedException

    def getuidvalidity(self):
        raise NotImplementedException

    def saveuidvalidity(self, newval):
        raise NotImplementedException

    def cachemessagelist(self):
        """Reads the message list from disk or network and stores it in
        memory for later use.  This list will not be re-read from disk or
        memory unless this function is called again."""
        raise NotImplementedException

    def getmessagelist(self):
        """Gets the current message list.
        You must call cachemessagelist() before calling this function!"""
        raise NotImplementedException

    def getmessage(self, uid):
        """Returns the content of the specified message."""
        raise NotImplementedException

    def savemessage(self, uid, content, flags):
        """Writes a new message, with the specified uid.
        If the uid is < 0, the backend should assign a new uid and return it.

        If the backend cannot assign a new uid, it returns the uid passed in
        WITHOUT saving the message.
        
        IMAP backend should be the only one that can assign a new uid.

        If the uid is > 0, the backend should set the uid to this, if it can.
        If it cannot set the uid to that, it will save it anyway.
        It will return the uid assigned in any case.
        """
        raise NotImplementedException

    def getmessageflags(self, uid):
        """Returns the flags for the specified message."""
        raise NotImplementedException

    def savemessageflags(self, uid, flags):
        """Sets the specified message's flags to the given set."""
        raise NotImplementedException

    def addmessageflags(self, uid, flags):
        """Adds the specified flags to the message's flag set.  If a given
        flag is already present, it will not be duplicated."""
        newflags = self.getmessageflags(uid)
        for flag in flags:
            if not flag in newflags:
                newflags.append(flag)
        newflags.sort()
        self.savemessageflags(uid, newflags)

    def deletemessageflags(self, uid, flags):
        """Removes each flag given from the message's flag set.  If a given
        flag is already removed, no action will be taken for that flag."""
        newflags = self.getmessageflags(uid)
        for flag in flags:
            if flag in newflags:
                newflags.remove(flag)
        newflags.sort()
        self.savemessageflags(uid, newflags)

    def deletemessage(self, uid):
        raise NotImplementedException

    def syncmessagesto(self, dest, applyto = None):
        """Syncs messages in this folder to the destination.
        If applyto is specified, it should be a list of folders (don't forget
        to include dest!) to which all write actions should be applied.
        It defaults to [dest] if not specified."""
        if applyto == None:
            applyto = [dest]

        # Pass 1 -- Look for messages in self with a negative uid.
        # These are messages in Maildirs that were not added by us.
        # Try to add them to the dests, and once that succeeds, get the
        # UID, add it to the others for real, add it to local for real,
        # and delete the fake one.

        for uid in self.getmessagelist().keys():
            if uid >= 0:
                continue
            successobject = None
            successuid = None
            message = self.getmessage(uid)
            flags = self.getmessageflags(uid)
            for tryappend in applyto:
                successuid = tryappend.savemessage(uid, message, flags)
                if successuid > 0:
                    successobject = tryappend
                    break
            # Did we succeed?
            if successobject != None:
                # Copy the message to the other remote servers.
                for appendserver in [x for x in applyto if x != successobject]:
                    appendserver.savemessage(successuid, message, flags)
                # Copy it to its new name on the local server and delete
                # the one without a UID.
                self.savemessage(successuid, message, flags)
                self.deletemessage(uid)
            else:
                # Did not find any server to take this message.  Delete
                pass

        # Pass 2 -- Look for messages present in self but not in dest.
        # If any, add them to dest.
        
        for uid in self.getmessagelist().keys():
            if uid < 0:                 # Ignore messages that pass 1 missed.
                continue
            if not uid in dest.getmessagelist():
                message = self.getmessage(uid)
                flags = self.getmessageflags(uid)
                for object in applyto:
                    object.savemessage(uid, message)
                    object.savemessageflags(uid, flags)

        # Pass 3 -- Look for message present in dest but not in self.
        # If any, delete them.

        for uid in dest.getmessagelist().keys():
            if not uid in self.getmessagelist():
                for object in applyto:
                    object.deletemessage(uid)

        # Now, the message lists should be identical wrt the uids present.
        # (except for potential negative uids that couldn't be placed
        # anywhere)
        
        # Pass 3 -- Look for any flag identity issues -- set dest messages
        # to have the same flags that we have here.

        for uid in self.getmessagelist().keys():
            if uid < 0:                 # Ignore messages missed by pass 1
                continue
            selfflags = self.getmessageflags(uid)
            destflags = dest.getmessageflags(uid)

            addflags = [x for x in selfflags if x not in destflags]
            if len(addflags):
                for object in applyto:
                    object.addmessageflags(addflags)

            delflags = [x for x in destflags if x not in selfflags]
            if len(delflags):
                for object in applyto:
                    object.deletemessageflags(delflags)

            
