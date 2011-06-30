#!/usr/bin/env python

# Program cluster_friend_graph.py
# Program to hierarchically agglomeratively cluster one's Facebook friends.
# 
# Author: Ruchira S. Datta
#
# Copyright 2009 by Ruchira S. Datta
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation fies (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM< DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM<
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Program to read in the graph of a person's Facebook friends and their mutual
relationships, cluster them using hierarchical agglomerative clustering, and
write them out in a tree to standard output and in a tree-ordered matrix to a
CSV file.
"""

import cPickle, sys, re, facebook

class node:
  def __init__(self, level, uid=None):
    self.level = level
    self.uid = uid
    self.children = []
    if uid:
      self.contained_uids = set([uid])
    else:
      self.contained_uids = set()

  def addChild(self, child):
    self.children = [child] + self.children
    self.contained_uids = self.contained_uids | child.contained_uids

  def adoptNieces(self, sibling):
    self.children = sibling.children + self.children
    self.contained_uids = self.contained_uids | sibling.contained_uids

  def printSelf(self, name_of_uid, indentLevel = 0):
    if self.uid:
      for i in range(indentLevel):
        sys.stdout.write(' ')
      if self.uid in name_of_uid:
        sys.stdout.write("%s" % name_of_uid[self.uid].encode('utf-8'))
      else:
        sys.stdout.write("%d" % self.uid)
    else:
      for i in range(indentLevel):
        sys.stdout.write(' ')
      sys.stdout.write("(\n")
      for i in range(len(self.children)):
        self.children[i].printSelf(name_of_uid, indentLevel + 1)
        if i < len(self.children) - 1:
          sys.stdout.write(",\n")
        else:
          sys.stdout.write("\n")
      for i in range(indentLevel):
        sys.stdout.write(' ')
      sys.stdout.write("):%g" % self.level)

  def addTreeOrderedUids(self, tree_ordered_uids, current_uid_index):
    if self.uid:
      tree_ordered_uids[current_uid_index] = self.uid
      return (current_uid_index + 1)
    else:
      for child in self.children:
        current_uid_index = child.addTreeOrderedUids(tree_ordered_uids,
                                                    current_uid_index)
      return current_uid_index

def main():
  if len(sys.argv) < 5:
    print "Usage: %s <friend_graph_pickle> <app_keys_pickle> <facebook_session_pkl> <output_file>" % sys.argv[0]
    sys.exit(0)
  friend_graph_pkl = sys.argv[1]
  app_keys_pkl = sys.argv[2]
  facebook_session_pkl = sys.argv[3]
  tree_ordered_friend_matrix_csv =sys.argv[4]
  print "Reading in friend_graph...",
  f = open(friend_graph_pkl)
  friend_graph = cPickle.load(f)
  f.close()
  print "done."
  uids = friend_graph.keys()
  uids.sort()
  print "%d uids in friend_graph" % len(uids)
  f = open(app_keys_pkl)
  keys = cPickle.load(f)
  f.close()
  fb = facebook.Facebook(keys['api_key'], keys['secret_key'])
  f = open(facebook_session_pkl)
  fb_session = cPickle.load(f)
  f.close()
  fb.session_key = fb_session['session_key']
  fb.secret = fb_session['secret']
  names_of_users = fb.users.getInfo(friend_graph.keys(), ['name'])
  name_of_uid = {}
  for v in names_of_users:
    name_of_uid[v['uid']] = v['name']
  friend_row = {}
  for friend0 in uids:
    friend_row[friend0] = set([friend1 for friend1 in uids if
                          friend_graph[friend0][friend1]])
  jaccard_distances = set()
  print "Computing Jaccard distances...",
  for i in range(len(uids)):
    for j in range(i):
      row0 = friend_row[uids[i]]
      row1 = friend_row[uids[j]]
      d = 1 - float(len(row0 & row1)) / len(row0 | row1)
      jaccard_distances.add( (d, uids[i], uids[j]) )
  print "done."
  sorted_jaccard_distances = list(jaccard_distances)
  print "Sorting Jaccard distances...",
  sorted_jaccard_distances.sort()
  print "done."
  nodes = {}
  roots = set()
  current_node_index = 0
  index_of_root_containing_uid = {}
  for uid in uids:
    new_node = node(-1.0, uid)
    nodes[current_node_index] = new_node
    roots.add(current_node_index)
    index_of_root_containing_uid[uid] = current_node_index
    current_node_index += 1
  print "Clustering friends..."
  for d, uid0, uid1 in sorted_jaccard_distances:
    if d >= 1.0:
      break
    i0 = index_of_root_containing_uid[uid0]
    i1 = index_of_root_containing_uid[uid1]
    if i0 == i1:
      continue
    print "d: %g uid0: %d uid1: %d i0: %d i1: %d" % (d, uid0, uid1, i0, i1)
    root0 = nodes[i0]
    root1 = nodes[i1]
    if d > root0.level and d > root1.level:
      # make a new node with root0 and root1 as children
      new_node = node(d)
      new_node.addChild(root0)
      new_node.addChild(root1)
      print "new node: %d with children %d and %d" % (current_node_index, 
                                                      i0, i1)
      nodes[current_node_index] = new_node
      for uid in new_node.contained_uids:
        index_of_root_containing_uid[uid] = current_node_index
      roots.add(current_node_index)
      current_node_index += 1
      roots.remove(i0)
      roots.remove(i1)
    elif d > root0.level and d == root1.level:
      # add root0 as a child of root1
      print "%d adopts child %d" % (i1, i0)
      root1.addChild(root0)
      for uid in root0.contained_uids:
        index_of_root_containing_uid[uid] = i1
      roots.remove(i0)
    elif d == root0.level and d > root1.level:
      # add root1 as a child of root0
      print "%d adopts child %d" % (i0, i1)
      root0.addChild(root1)
      for uid in root1.contained_uids:
        index_of_root_containing_uid[uid] = i0
      roots.remove(i1)
    elif d == root0.level and d == root1.level:
      # merge root1 into root0
      print "%d adopts children of dead sibling %d" % (i0, i1)
      root0.adoptNieces(root1)
      for uid in root1.contained_uids:
        index_of_root_containing_uid[uid] = i0
      roots.remove(i1)
      nodes[i1] = None
  print "Done clustering friends."
  for root in roots:
    nodes[root].printSelf(name_of_uid)
    sys.stdout.write("\n")
  current_uid_index = 0
  tree_ordered_uids = {}
  for root in roots:
    nodes[root].addTreeOrderedUids(tree_ordered_uids, current_uid_index)
  f = open(tree_ordered_friend_matrix_csv, "w")
  f.write("Friend,")
  for j in range(len(tree_ordered_uids)):
    f.write("%d," % tree_ordered_uids[j])
  f.write("\n")
  for i in range(len(tree_ordered_uids)):
    f.write("%16d," % tree_ordered_uids[i])
    for j in range(len(tree_ordered_uids)):
      if friend_graph[tree_ordered_uids[i]][tree_ordered_uids[j]]:
        f.write("1,")
      else:
        f.write("0,")
    f.write("\n")
  f.close()

if __name__ == '__main__':
  main()
